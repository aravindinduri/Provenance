"""
app/modules/graph/repository.py — Data access layer for tenant supply graph edges.

CRITICAL TENANT ISOLATION:
Every query on supplier_relationships MUST be filtered by org_id.
Supplier relationships encode who-buys-from-whom and are strictly tenant-isolated.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Select, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.pagination import apply_cursor_to_query, encode_cursor
from app.modules.companies.models import Company
from app.modules.graph.models import CompanyLocation, Location, SupplierRelationship
from app.modules.organizations.models import Organization
from app.modules.risk.models import RiskAssessment


class GraphRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Suppliers (direct supply edges to tenant) ───────────────────────────

    async def get_supplier_by_id(
        self, supplier_id: uuid.UUID, org_id: uuid.UUID
    ) -> tuple[SupplierRelationship, Company] | None:
        """Fetch a direct supplier relationship with joined Company."""
        stmt = (
            select(SupplierRelationship, Company)
            .join(Company, SupplierRelationship.from_company_id == Company.id)
            .where(
                SupplierRelationship.id == supplier_id,
                SupplierRelationship.org_id == org_id,
                SupplierRelationship.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if not row:
            return None
        return row[0], row[1]

    async def list_suppliers(
        self,
        *,
        org_id: uuid.UUID,
        category: str | None = None,
        criticality: int | None = None,
        tier: int | None = None,
        active_only: bool = True,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[tuple[SupplierRelationship, Company]], str | None, bool]:
        """List direct suppliers for an org with cursor pagination."""
        limit = min(max(1, limit), 100)
        stmt: Select = (
            select(SupplierRelationship, Company)
            .join(Company, SupplierRelationship.from_company_id == Company.id)
            .where(
                SupplierRelationship.org_id == org_id,
                SupplierRelationship.deleted_at.is_(None),
                or_(
                    SupplierRelationship.to_org_id == org_id,
                    SupplierRelationship.relationship_type == "supplies_to",
                ),
            )
        )

        if active_only:
            stmt = stmt.where(SupplierRelationship.valid_to.is_(None))

        if category:
            stmt = stmt.where(SupplierRelationship.category == category)

        if criticality is not None:
            stmt = stmt.where(SupplierRelationship.criticality == criticality)

        if tier is not None:
            stmt = stmt.where(SupplierRelationship.tier == tier)

        stmt = apply_cursor_to_query(
            stmt,
            cursor=cursor,
            sort_column=SupplierRelationship.created_at,
            id_column=SupplierRelationship.id,
            is_datetime=True,
            descending=True,
        )

        stmt = stmt.order_by(
            SupplierRelationship.created_at.desc(),
            SupplierRelationship.id.desc(),
        ).limit(limit + 1)

        result = await self.db.execute(stmt)
        rows = list(result.all())

        has_more = len(rows) > limit
        if has_more:
            items = rows[:limit]
            last_rel, _ = items[-1]
            next_cursor = encode_cursor(last_rel.created_at, last_rel.id)
        else:
            items = rows
            next_cursor = None

        return items, next_cursor, has_more

    async def create_supplier(
        self,
        *,
        org_id: uuid.UUID,
        from_company_id: uuid.UUID,
        tier: int = 1,
        criticality: int = 3,
        annual_spend_usd: float | None = None,
        category: str | None = None,
        single_source: bool = False,
        lead_time_days: int | None = None,
        confidence: float = 1.0,
        source: str = "user_declared",
    ) -> SupplierRelationship:
        """Create a direct supplier edge to this organization."""
        rel = SupplierRelationship(
            org_id=org_id,
            from_company_id=from_company_id,
            to_org_id=org_id,
            relationship_type="supplies_to",
            tier=tier,
            criticality=criticality,
            annual_spend_usd=annual_spend_usd,
            category=category,
            single_source=single_source,
            lead_time_days=lead_time_days,
            confidence=confidence,
            source=source,
            valid_from=date.today(),
        )
        self.db.add(rel)
        await self.db.flush()
        return rel

    async def update_supplier(
        self,
        *,
        supplier_id: uuid.UUID,
        org_id: uuid.UUID,
        **kwargs: Any,
    ) -> SupplierRelationship | None:
        """Update fields on a supplier relationship."""
        stmt = select(SupplierRelationship).where(
            SupplierRelationship.id == supplier_id,
            SupplierRelationship.org_id == org_id,
            SupplierRelationship.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        rel = result.scalar_one_or_none()
        if not rel:
            return None

        for k, v in kwargs.items():
            if v is not None and hasattr(rel, k):
                setattr(rel, k, v)

        await self.db.flush()
        return rel

    async def soft_delete_supplier(
        self, supplier_id: uuid.UUID, org_id: uuid.UUID
    ) -> bool:
        """Soft-delete a supplier edge (sets valid_to and deleted_at)."""
        stmt = select(SupplierRelationship).where(
            SupplierRelationship.id == supplier_id,
            SupplierRelationship.org_id == org_id,
            SupplierRelationship.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        rel = result.scalar_one_or_none()
        if not rel:
            return False

        now = datetime.now()
        rel.valid_to = now.date()
        rel.deleted_at = now
        await self.db.flush()
        return True

    # ── Generic Graph Relationships ─────────────────────────────────────────

    async def get_relationship_by_id(
        self, rel_id: uuid.UUID, org_id: uuid.UUID
    ) -> tuple[SupplierRelationship, Company, Company | None] | None:
        """Fetch an edge with from_company and optional to_company."""
        from_comp = aliased(Company, name="from_comp")
        to_comp = aliased(Company, name="to_comp")

        stmt = (
            select(SupplierRelationship, from_comp, to_comp)
            .join(from_comp, SupplierRelationship.from_company_id == from_comp.id)
            .outerjoin(to_comp, SupplierRelationship.to_company_id == to_comp.id)
            .where(
                SupplierRelationship.id == rel_id,
                SupplierRelationship.org_id == org_id,
                SupplierRelationship.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if not row:
            return None
        return row[0], row[1], row[2]

    async def list_relationships(
        self,
        *,
        org_id: uuid.UUID,
        relationship_type: str | None = None,
        from_company_id: uuid.UUID | None = None,
        to_company_id: uuid.UUID | None = None,
        tier: int | None = None,
        active_only: bool = True,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[tuple[SupplierRelationship, Company, Company | None]], str | None, bool]:
        """List graph edges with cursor pagination."""
        limit = min(max(1, limit), 100)
        from_comp = aliased(Company, name="from_comp")
        to_comp = aliased(Company, name="to_comp")

        stmt: Select = (
            select(SupplierRelationship, from_comp, to_comp)
            .join(from_comp, SupplierRelationship.from_company_id == from_comp.id)
            .outerjoin(to_comp, SupplierRelationship.to_company_id == to_comp.id)
            .where(
                SupplierRelationship.org_id == org_id,
                SupplierRelationship.deleted_at.is_(None),
            )
        )

        if active_only:
            stmt = stmt.where(SupplierRelationship.valid_to.is_(None))

        if relationship_type:
            stmt = stmt.where(SupplierRelationship.relationship_type == relationship_type)

        if from_company_id:
            stmt = stmt.where(SupplierRelationship.from_company_id == from_company_id)

        if to_company_id:
            stmt = stmt.where(SupplierRelationship.to_company_id == to_company_id)

        if tier is not None:
            stmt = stmt.where(SupplierRelationship.tier == tier)

        stmt = apply_cursor_to_query(
            stmt,
            cursor=cursor,
            sort_column=SupplierRelationship.created_at,
            id_column=SupplierRelationship.id,
            is_datetime=True,
            descending=True,
        )

        stmt = stmt.order_by(
            SupplierRelationship.created_at.desc(),
            SupplierRelationship.id.desc(),
        ).limit(limit + 1)

        result = await self.db.execute(stmt)
        rows = list(result.all())

        has_more = len(rows) > limit
        if has_more:
            items = rows[:limit]
            last_rel, _, _ = items[-1]
            next_cursor = encode_cursor(last_rel.created_at, last_rel.id)
        else:
            items = rows
            next_cursor = None

        return items, next_cursor, has_more

    async def create_relationship(
        self,
        *,
        org_id: uuid.UUID,
        from_company_id: uuid.UUID,
        to_company_id: uuid.UUID | None = None,
        to_org_id: uuid.UUID | None = None,
        relationship_type: str = "supplies_to",
        tier: int | None = None,
        criticality: int | None = None,
        annual_spend_usd: float | None = None,
        category: str | None = None,
        single_source: bool = False,
        lead_time_days: int | None = None,
        confidence: float = 1.0,
        source: str = "user_declared",
    ) -> SupplierRelationship:
        """Create a graph edge for an organization."""
        rel = SupplierRelationship(
            org_id=org_id,
            from_company_id=from_company_id,
            to_company_id=to_company_id,
            to_org_id=to_org_id,
            relationship_type=relationship_type,
            tier=tier,
            criticality=criticality,
            annual_spend_usd=annual_spend_usd,
            category=category,
            single_source=single_source,
            lead_time_days=lead_time_days,
            confidence=confidence,
            source=source,
            valid_from=date.today(),
        )
        self.db.add(rel)
        await self.db.flush()
        return rel

    async def update_relationship(
        self,
        *,
        rel_id: uuid.UUID,
        org_id: uuid.UUID,
        **kwargs: Any,
    ) -> SupplierRelationship | None:
        """Update attributes on an edge."""
        stmt = select(SupplierRelationship).where(
            SupplierRelationship.id == rel_id,
            SupplierRelationship.org_id == org_id,
            SupplierRelationship.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        rel = result.scalar_one_or_none()
        if not rel:
            return None

        for k, v in kwargs.items():
            if v is not None and hasattr(rel, k):
                setattr(rel, k, v)

        await self.db.flush()
        return rel

    async def soft_delete_relationship(
        self, rel_id: uuid.UUID, org_id: uuid.UUID
    ) -> bool:
        """Soft-delete a relationship edge."""
        stmt = select(SupplierRelationship).where(
            SupplierRelationship.id == rel_id,
            SupplierRelationship.org_id == org_id,
            SupplierRelationship.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        rel = result.scalar_one_or_none()
        if not rel:
            return False

        now = datetime.now()
        rel.valid_to = now.date()
        rel.deleted_at = now
        await self.db.flush()
        return True

    # ── Phase 7 Graph Traversal & Path Discovery ─────────────────────────────

    async def traverse_graph(
        self,
        *,
        org_id: uuid.UUID,
        root_id: uuid.UUID | None = None,
        max_depth: int = 3,
        relationship_types: list[str] | None = None,
        limit: int = 300,
    ) -> tuple[list[dict[str, Any]], bool]:
        """
        Recursive CTE graph traversal with depth cap, node cap, and cycle guard.
        Per arch §8 & §Phase 7:
          - Cycle guard: NOT (r.from_company_id = ANY(x.path)) AND NOT (r.id = ANY(x.edge_path))
          - Depth capped at 5 max
          - Capped at `limit` (max 5000)
          - Multi-tenant isolated by org_id
        """
        depth_cap = min(max(1, max_depth), 5)
        limit_cap = min(max(1, limit), 5000)

        # Attempt high-performance PostgreSQL recursive CTE
        try:
            sql = text(
                """
                WITH RECURSIVE reach AS (
                    SELECT r.id AS edge_id,
                           r.from_company_id,
                           r.to_company_id,
                           r.to_org_id,
                           r.relationship_type,
                           r.tier,
                           r.criticality,
                           r.annual_spend_usd,
                           r.single_source,
                           r.lead_time_days,
                           r.confidence,
                           r.source,
                           1 AS depth,
                           ARRAY[r.from_company_id] AS path,
                           ARRAY[r.id] AS edge_path,
                           r.confidence::numeric(5, 4) AS path_confidence
                    FROM supplier_relationships r
                    WHERE r.org_id = :org_id
                      AND r.deleted_at IS NULL
                      AND r.valid_to IS NULL
                      AND (
                          (CAST(:root_id AS UUID) IS NULL AND (r.to_org_id = :org_id OR r.relationship_type = 'supplies_to' OR r.tier = 1))
                          OR
                          (CAST(:root_id AS UUID) IS NOT NULL AND (r.from_company_id = CAST(:root_id AS UUID) OR r.to_company_id = CAST(:root_id AS UUID)))
                      )
                      AND (:filter_types = false OR r.relationship_type = ANY(CAST(:types AS TEXT[])))
                  UNION ALL
                    SELECT r.id AS edge_id,
                           r.from_company_id,
                           r.to_company_id,
                           r.to_org_id,
                           r.relationship_type,
                           r.tier,
                           r.criticality,
                           r.annual_spend_usd,
                           r.single_source,
                           r.lead_time_days,
                           r.confidence,
                           r.source,
                           x.depth + 1,
                           x.path || r.from_company_id,
                           x.edge_path || r.id,
                           (x.path_confidence * r.confidence)::numeric(5, 4)
                    FROM supplier_relationships r
                    JOIN reach x ON (
                        r.to_company_id = x.from_company_id
                        OR
                        (x.to_company_id IS NOT NULL AND r.from_company_id = x.to_company_id)
                    )
                    WHERE x.depth < :max_depth
                      AND r.org_id = :org_id
                      AND r.deleted_at IS NULL
                      AND r.valid_to IS NULL
                      AND NOT (r.from_company_id = ANY(x.path))
                      AND NOT (r.id = ANY(x.edge_path))
                      AND (:filter_types = false OR r.relationship_type = ANY(CAST(:types AS TEXT[])))
                )
                SELECT DISTINCT ON (edge_id) *
                FROM reach
                LIMIT :limit_plus_one;
                """
            )
            result = await self.db.execute(
                sql,
                {
                    "org_id": org_id,
                    "root_id": root_id,
                    "max_depth": depth_cap,
                    "filter_types": bool(relationship_types),
                    "types": relationship_types or [],
                    "limit_plus_one": limit_cap + 1,
                },
            )
            raw_rows = [dict(row._mapping) for row in result.all()]
            has_more = len(raw_rows) > limit_cap
            return raw_rows[:limit_cap], has_more
        except Exception:
            # Fallback in-memory traversal (for SQLite / unit tests where PostgreSQL array syntax isn't available)
            return await self._in_memory_traverse(
                org_id=org_id,
                root_id=root_id,
                max_depth=depth_cap,
                relationship_types=relationship_types,
                limit=limit_cap,
            )

    async def _in_memory_traverse(
        self,
        *,
        org_id: uuid.UUID,
        root_id: uuid.UUID | None,
        max_depth: int,
        relationship_types: list[str] | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Pure Python traversal with cycle guard and depth limits for SQLite/mock test compatibility."""
        stmt = select(SupplierRelationship).where(
            SupplierRelationship.org_id == org_id,
            SupplierRelationship.deleted_at.is_(None),
            SupplierRelationship.valid_to.is_(None),
        )
        if relationship_types:
            stmt = stmt.where(SupplierRelationship.relationship_type.in_(relationship_types))

        all_rels = list((await self.db.execute(stmt)).scalars().all())

        # Build adjacency maps
        from collections import defaultdict, deque
        outgoing: dict[uuid.UUID, list[SupplierRelationship]] = defaultdict(list)
        incoming: dict[uuid.UUID, list[SupplierRelationship]] = defaultdict(list)

        for rel in all_rels:
            outgoing[rel.from_company_id].append(rel)
            if rel.to_company_id:
                incoming[rel.to_company_id].append(rel)

        # Determine start edges
        start_edges: list[SupplierRelationship] = []
        if root_id is None:
            for rel in all_rels:
                if rel.to_org_id == org_id or rel.relationship_type == "supplies_to" or rel.tier == 1:
                    start_edges.append(rel)
        else:
            for rel in all_rels:
                if rel.from_company_id == root_id or rel.to_company_id == root_id:
                    start_edges.append(rel)

        collected_edges: dict[uuid.UUID, dict[str, Any]] = {}
        # Queue item: (rel, depth, visited_company_ids, visited_edge_ids, path_confidence)
        queue = deque(
            [
                (
                    e,
                    1,
                    [e.from_company_id],
                    [e.id],
                    float(e.confidence or 1.0),
                )
                for e in start_edges
            ]
        )

        while queue and len(collected_edges) <= limit:
            rel, depth, path, edge_path, conf = queue.popleft()
            if rel.id not in collected_edges:
                collected_edges[rel.id] = {
                    "edge_id": rel.id,
                    "from_company_id": rel.from_company_id,
                    "to_company_id": rel.to_company_id,
                    "to_org_id": rel.to_org_id,
                    "relationship_type": rel.relationship_type,
                    "tier": rel.tier,
                    "criticality": rel.criticality,
                    "annual_spend_usd": float(rel.annual_spend_usd) if rel.annual_spend_usd is not None else None,
                    "single_source": rel.single_source,
                    "lead_time_days": rel.lead_time_days,
                    "confidence": float(rel.confidence or 1.0),
                    "source": rel.source,
                    "depth": depth,
                    "path_confidence": conf,
                }

            if depth < max_depth:
                # Upstream candidates: rels where to_company_id matches this from_company_id
                upstream = incoming.get(rel.from_company_id, [])
                for next_rel in upstream:
                    if next_rel.from_company_id not in path and next_rel.id not in edge_path:
                        queue.append(
                            (
                                next_rel,
                                depth + 1,
                                path + [next_rel.from_company_id],
                                edge_path + [next_rel.id],
                                conf * float(next_rel.confidence or 1.0),
                            )
                        )
                # Downstream candidates (if searching outward)
                if rel.to_company_id:
                    downstream = outgoing.get(rel.to_company_id, [])
                    for next_rel in downstream:
                        if next_rel.from_company_id not in path and next_rel.id not in edge_path:
                            queue.append(
                                (
                                    next_rel,
                                    depth + 1,
                                    path + [next_rel.from_company_id],
                                    edge_path + [next_rel.id],
                                    conf * float(next_rel.confidence or 1.0),
                                )
                            )

        edges_list = list(collected_edges.values())
        has_more = len(edges_list) > limit
        return edges_list[:limit], has_more

    async def find_paths(
        self,
        *,
        org_id: uuid.UUID,
        from_company_id: uuid.UUID,
        to_company_id: uuid.UUID | None = None,
        max_depth: int = 5,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Finds exposure paths from an affected upstream company to the tenant org
        or to a specified downstream target company.
        Cycle-guarded, deterministic, calculates path confidence as product of edge confidences.
        """
        depth_cap = min(max(1, max_depth), 5)
        limit_cap = min(max(1, limit), 50)

        try:
            sql = text(
                """
                WITH RECURSIVE path_reach AS (
                    SELECT r.id AS edge_id,
                           r.from_company_id,
                           r.to_company_id,
                           r.to_org_id,
                           r.relationship_type,
                           r.tier,
                           r.criticality,
                           r.annual_spend_usd,
                           r.confidence,
                           r.source,
                           1 AS depth,
                           ARRAY[r.from_company_id] AS path,
                           ARRAY[r.id] AS edge_path,
                           r.confidence::numeric(5, 4) AS path_confidence
                    FROM supplier_relationships r
                    WHERE r.from_company_id = :from_id
                      AND r.org_id = :org_id
                      AND r.deleted_at IS NULL
                      AND r.valid_to IS NULL
                  UNION ALL
                    SELECT r.id AS edge_id,
                           r.from_company_id,
                           r.to_company_id,
                           r.to_org_id,
                           r.relationship_type,
                           r.tier,
                           r.criticality,
                           r.annual_spend_usd,
                           r.confidence,
                           r.source,
                           x.depth + 1,
                           x.path || r.from_company_id,
                           x.edge_path || r.id,
                           (x.path_confidence * r.confidence)::numeric(5, 4)
                    FROM supplier_relationships r
                    JOIN path_reach x ON r.from_company_id = x.to_company_id
                    WHERE x.depth < :max_depth
                      AND r.org_id = :org_id
                      AND r.deleted_at IS NULL
                      AND r.valid_to IS NULL
                      AND NOT (r.from_company_id = ANY(x.path))
                      AND NOT (r.id = ANY(x.edge_path))
                )
                SELECT *
                FROM path_reach
                WHERE (
                    (:to_id IS NULL AND (to_org_id = :org_id OR relationship_type = 'supplies_to'))
                    OR
                    (:to_id IS NOT NULL AND (to_company_id = :to_id OR to_org_id = :to_id))
                )
                ORDER BY path_confidence DESC, depth ASC
                LIMIT :limit;
                """
            )
            result = await self.db.execute(
                sql,
                {
                    "org_id": org_id,
                    "from_id": from_company_id,
                    "to_id": to_company_id,
                    "max_depth": depth_cap,
                    "limit": limit_cap,
                },
            )
            return [dict(row._mapping) for row in result.all()]
        except Exception:
            return await self._in_memory_find_paths(
                org_id=org_id,
                from_company_id=from_company_id,
                to_company_id=to_company_id,
                max_depth=depth_cap,
                limit=limit_cap,
            )

    async def _in_memory_find_paths(
        self,
        *,
        org_id: uuid.UUID,
        from_company_id: uuid.UUID,
        to_company_id: uuid.UUID | None,
        max_depth: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """In-memory path search fallback for testing."""
        stmt = select(SupplierRelationship).where(
            SupplierRelationship.org_id == org_id,
            SupplierRelationship.deleted_at.is_(None),
            SupplierRelationship.valid_to.is_(None),
        )
        all_rels = list((await self.db.execute(stmt)).scalars().all())

        from collections import defaultdict
        outgoing: dict[uuid.UUID, list[SupplierRelationship]] = defaultdict(list)
        for rel in all_rels:
            outgoing[rel.from_company_id].append(rel)

        found_paths: list[dict[str, Any]] = []

        def dfs(
            current_cid: uuid.UUID,
            current_depth: int,
            visited_cids: list[uuid.UUID],
            visited_eids: list[uuid.UUID],
            last_rel: SupplierRelationship,
            path_conf: float,
        ) -> None:
            if len(found_paths) >= limit:
                return

            # Check target condition
            is_target = False
            if to_company_id is None:
                if last_rel.to_org_id == org_id or last_rel.relationship_type == "supplies_to":
                    is_target = True
            else:
                if last_rel.to_company_id == to_company_id or last_rel.to_org_id == to_company_id:
                    is_target = True

            if is_target:
                found_paths.append(
                    {
                        "edge_id": last_rel.id,
                        "from_company_id": last_rel.from_company_id,
                        "to_company_id": last_rel.to_company_id,
                        "to_org_id": last_rel.to_org_id,
                        "relationship_type": last_rel.relationship_type,
                        "tier": last_rel.tier,
                        "criticality": last_rel.criticality,
                        "annual_spend_usd": float(last_rel.annual_spend_usd) if last_rel.annual_spend_usd is not None else None,
                        "confidence": float(last_rel.confidence or 1.0),
                        "source": last_rel.source,
                        "depth": current_depth,
                        "path": visited_cids,
                        "edge_path": visited_eids,
                        "path_confidence": round(path_conf, 4),
                    }
                )
                return

            if current_depth >= max_depth:
                return

            # Advance to next hop
            target_cid = last_rel.to_company_id
            if not target_cid or target_cid in visited_cids:
                return

            for nxt in outgoing.get(target_cid, []):
                if nxt.from_company_id not in visited_cids and nxt.id not in visited_eids:
                    dfs(
                        target_cid,
                        current_depth + 1,
                        visited_cids + [nxt.from_company_id],
                        visited_eids + [nxt.id],
                        nxt,
                        path_conf * float(nxt.confidence or 1.0),
                    )

        # Start from from_company_id
        for rel in outgoing.get(from_company_id, []):
            dfs(
                from_company_id,
                1,
                [rel.from_company_id],
                [rel.id],
                rel,
                float(rel.confidence or 1.0),
            )

        found_paths.sort(key=lambda p: (-p["path_confidence"], p["depth"]))
        return found_paths[:limit]

    async def get_companies_by_ids(
        self, company_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, Company]:
        """Fetch companies by a list of UUIDs."""
        if not company_ids:
            return {}
        stmt = select(Company).where(Company.id.in_(company_ids))
        companies = (await self.db.execute(stmt)).scalars().all()
        return {c.id: c for c in companies}

    async def get_company_locations(
        self, company_ids: list[uuid.UUID]
    ) -> list[tuple[CompanyLocation, Location]]:
        """Fetch primary locations for a list of company IDs."""
        if not company_ids:
            return []
        stmt = (
            select(CompanyLocation, Location)
            .join(Location, CompanyLocation.location_id == Location.id)
            .where(
                CompanyLocation.company_id.in_(company_ids),
                CompanyLocation.valid_to.is_(None),
            )
        )
        return list((await self.db.execute(stmt)).all())

    async def get_company_risk_assessments(
        self, org_id: uuid.UUID, company_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[str, float]]:
        """
        Fetch latest severity_band and impact_score for companies in an organization.
        Returns dict mapping company_id -> (severity_band, impact_score).
        """
        if not company_ids:
            return {}
        stmt = (
            select(
                RiskAssessment.company_id,
                RiskAssessment.severity_band,
                RiskAssessment.impact_score,
            )
            .where(
                RiskAssessment.org_id == org_id,
                RiskAssessment.company_id.in_(company_ids),
            )
            .order_by(RiskAssessment.impact_score.desc())
        )
        rows = (await self.db.execute(stmt)).all()
        risk_map: dict[uuid.UUID, tuple[str, float]] = {}
        for cid, band, score in rows:
            if cid not in risk_map:
                risk_map[cid] = (str(band), float(score))
        return risk_map

    async def get_organization(self, org_id: uuid.UUID) -> Organization | None:
        """Fetch organization record by ID."""
        stmt = select(Organization).where(Organization.id == org_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

