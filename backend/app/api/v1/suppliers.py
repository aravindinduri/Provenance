"""
/v1/suppliers — Direct supplier management for the tenant.

Endpoints:
  GET    /suppliers             — list tenant's suppliers (cursor-paginated)
  POST   /suppliers             — add a supplier to tenant
  GET    /suppliers/{id}        — get supplier details
  PATCH  /suppliers/{id}        — update supplier attributes
  DELETE /suppliers/{id}        — soft-delete supplier
"""

from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.base import CurrentUser
from app.core.deps import require_permission
from app.core.errors import bad_request, not_found
from app.core.pagination import PaginationMeta
from app.db.session import get_db
from app.modules.companies.service import CompanyNotFound
from app.modules.graph.bulk_service import (
    bulk_job_store,
    execute_bulk_supplier_job,
    parse_supplier_csv,
)
from app.modules.graph.schemas import (
    BulkRowError,
    BulkSupplierJobOut,
    BulkSupplierUploadRequest,
    PaginatedSuppliers,
    SupplierCreate,
    SupplierDetailOut,
    SupplierOut,
    SupplierUpdate,
)
from app.modules.graph.service import GraphService, SupplierNotFound

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _service(db: AsyncSession) -> GraphService:
    return GraphService(db)


def _get_org_id(current_user: CurrentUser) -> uuid.UUID:
    if not current_user.org_id:
        raise ValueError("Tenant org_id is required for supplier operations")
    return uuid.UUID(current_user.org_id)


@router.get(
    "",
    response_model=PaginatedSuppliers,
    summary="List organization suppliers",
)
async def list_suppliers(
    request: Request,
    category: str | None = Query(None, description="Filter by category"),
    criticality: int | None = Query(None, ge=1, le=5, description="Filter by criticality (1-5)"),
    tier: int | None = Query(None, ge=1, le=10, description="Filter by tier"),
    active_only: bool = Query(True, description="Only return active suppliers"),
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Page limit (max 100)"),
    current_user: CurrentUser = Depends(require_permission("suppliers:read")),
    db: AsyncSession = Depends(get_db),
) -> PaginatedSuppliers:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    items, next_cursor, has_more = await svc.list_suppliers(
        org_id=org_id,
        category=category,
        criticality=criticality,
        tier=tier,
        active_only=active_only,
        cursor=cursor,
        limit=limit,
    )

    return PaginatedSuppliers(
        data=items,
        pagination=PaginationMeta(next_cursor=next_cursor, has_more=has_more),
    )


@router.post(
    "",
    response_model=SupplierOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a supplier to the organization",
)
async def create_supplier(
    request: Request,
    payload: SupplierCreate,
    current_user: CurrentUser = Depends(require_permission("suppliers:write")),
    db: AsyncSession = Depends(get_db),
) -> SupplierOut:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    try:
        supplier = await svc.create_supplier(org_id, payload)
        await db.commit()
        return supplier
    except CompanyNotFound as exc:
        return not_found(request, detail=str(exc))  # type: ignore[return-value]



@router.post(
    "/bulk",
    response_model=BulkSupplierJobOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Bulk add suppliers via CSV or JSON (async, returns job_id)",
)
async def bulk_create_suppliers(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_permission("suppliers:write")),
) -> BulkSupplierJobOut:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    content_type = request.headers.get("content-type", "")
    csv_text: str = ""
    rows: list[SupplierCreate] = []
    parse_errors: list[BulkRowError] = []

    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded_file = form.get("file")
        if not uploaded_file:
            return bad_request(  # type: ignore[return-value]
                request, detail="Missing 'file' field in multipart form upload"
            )
        raw_bytes = await uploaded_file.read()  # type: ignore[union-attr]
        try:
            csv_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            csv_text = raw_bytes.decode("latin-1", errors="replace")
        rows, parse_errors = parse_supplier_csv(csv_text)
    elif "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            return bad_request(request, detail="Invalid JSON payload")  # type: ignore[return-value]
        if isinstance(data, dict):
            if "raw_csv" in data and data["raw_csv"]:
                rows, parse_errors = parse_supplier_csv(str(data["raw_csv"]))
            elif "rows" in data and isinstance(data["rows"], list):
                for idx, r in enumerate(data["rows"], start=1):
                    try:
                        rows.append(SupplierCreate.model_validate(r))
                    except Exception as exc:
                        parse_errors.append(
                            BulkRowError(row=idx, error=str(exc))
                        )
            else:
                return bad_request(  # type: ignore[return-value]
                    request,
                    detail="JSON must contain 'raw_csv' string or 'rows' array",
                )
        elif isinstance(data, list):
            for idx, r in enumerate(data, start=1):
                try:
                    rows.append(SupplierCreate.model_validate(r))
                except Exception as exc:
                    parse_errors.append(BulkRowError(row=idx, error=str(exc)))
        else:
            return bad_request(  # type: ignore[return-value]
                request, detail="Expected JSON object or array"
            )
    else:
        # Raw CSV / plain text
        raw_bytes = await request.body()
        if not raw_bytes:
            return bad_request(  # type: ignore[return-value]
                request, detail="Empty request body. Send CSV or JSON."
            )
        try:
            csv_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            csv_text = raw_bytes.decode("latin-1", errors="replace")
        rows, parse_errors = parse_supplier_csv(csv_text)

    total = len(rows) + len(parse_errors)
    job = bulk_job_store.create_job(org_id=org_id, total_rows=total)

    # Dispatch async background worker
    background_tasks.add_task(
        execute_bulk_supplier_job,
        job_id=job.job_id,
        org_id=org_id,
        rows=rows,
        parse_errors=parse_errors,
    )

    return job


@router.get(
    "/bulk/{job_id}",
    response_model=BulkSupplierJobOut,
    summary="Get bulk supplier import job status and progress",
)
async def get_bulk_supplier_job(
    request: Request,
    job_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("suppliers:read")),
) -> BulkSupplierJobOut:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    job = bulk_job_store.get_job(job_id, org_id)
    if not job:
        return not_found(request, detail=f"Bulk job {job_id} not found")  # type: ignore[return-value]
    return job


@router.get(
    "/{supplier_id}",
    response_model=SupplierDetailOut,
    summary="Get supplier details",
)
async def get_supplier(
    request: Request,
    supplier_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("suppliers:read")),
    db: AsyncSession = Depends(get_db),
) -> SupplierDetailOut:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    try:
        return await svc.get_supplier_detail(supplier_id, org_id)
    except SupplierNotFound:
        return not_found(request, detail=f"Supplier {supplier_id} not found")  # type: ignore[return-value]


@router.patch(
    "/{supplier_id}",
    response_model=SupplierOut,
    summary="Update supplier attributes",
)
async def update_supplier(
    request: Request,
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
    current_user: CurrentUser = Depends(require_permission("suppliers:write")),
    db: AsyncSession = Depends(get_db),
) -> SupplierOut:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    try:
        supplier = await svc.update_supplier(supplier_id, org_id, payload)
        await db.commit()
        return supplier
    except SupplierNotFound:
        return not_found(request, detail=f"Supplier {supplier_id} not found")  # type: ignore[return-value]


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Soft-delete supplier",
)
async def delete_supplier(
    request: Request,
    supplier_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("suppliers:write")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        org_id = _get_org_id(current_user)
    except ValueError as exc:
        return bad_request(request, detail=str(exc))  # type: ignore[return-value]

    svc = _service(db)
    try:
        await svc.delete_supplier(supplier_id, org_id)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except SupplierNotFound:
        return not_found(request, detail=f"Supplier {supplier_id} not found")  # type: ignore[return-value]
