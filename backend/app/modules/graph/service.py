"""
app/modules/graph/service.py — Business logic for suppliers and relationships.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.companies.repository import CompanyRepository
from app.modules.companies.schemas import CompanySummaryOut
from app.modules.companies.service import CompanyNotFound, CompanyService
from app.modules.graph.repository import GraphRepository
from app.modules.graph.schemas import (
    GraphData,
    GraphEdge,
    GraphMetadata,
    GraphNode,
    GraphPath,
    GraphPathsResponse,
    RelationshipCreate,
    RelationshipOut,
    RelationshipUpdate,
    SupplierCreate,
    SupplierDetailOut,
    SupplierOut,
    SupplierUpdate,
)



def _to_float(val: object | None) -> float | None:
    return float(val) if val is not None else None


class SupplierNotFound(Exception):
    def __init__(self, supplier_id: uuid.UUID) -> None:
        super().__init__(f"Supplier {supplier_id} not found")
        self.supplier_id = supplier_id


class RelationshipNotFound(Exception):
    def __init__(self, rel_id: uuid.UUID) -> None:
        super().__init__(f"Relationship {rel_id} not found")
        self.rel_id = rel_id


class GraphService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = GraphRepository(db)
        self.company_repo = CompanyRepository(db)
        self.company_svc = CompanyService(db)

    # ── Suppliers ───────────────────────────────────────────────────────────

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
    ) -> tuple[list[SupplierOut], str | None, bool]:
        rows, next_cursor, has_more = await self.repo.list_suppliers(
            org_id=org_id,
            category=category,
            criticality=criticality,
            tier=tier,
            active_only=active_only,
            cursor=cursor,
            limit=limit,
        )

        items = [
            SupplierOut(
                id=rel.id,
                org_id=rel.org_id,
                company_id=comp.id,
                company=CompanySummaryOut.model_validate(comp),
                relationship_type=rel.relationship_type,
                tier=rel.tier,
                criticality=rel.criticality,
                annual_spend_usd=_to_float(rel.annual_spend_usd),
                category=rel.category,
                single_source=rel.single_source,
                lead_time_days=rel.lead_time_days,
                confidence=float(rel.confidence),
                source=rel.source,
                valid_from=rel.valid_from,
                valid_to=rel.valid_to,
                created_at=rel.created_at,
                updated_at=rel.updated_at,
            )
            for rel, comp in rows
        ]

        return items, next_cursor, has_more

    async def get_supplier(
        self, supplier_id: uuid.UUID, org_id: uuid.UUID
    ) -> SupplierOut:
        result = await self.repo.get_supplier_by_id(supplier_id, org_id)
        if not result:
            raise SupplierNotFound(supplier_id)

        rel, comp = result
        return SupplierOut(
            id=rel.id,
            org_id=rel.org_id,
            company_id=comp.id,
            company=CompanySummaryOut.model_validate(comp),
            relationship_type=rel.relationship_type,
            tier=rel.tier,
            criticality=rel.criticality,
            annual_spend_usd=_to_float(rel.annual_spend_usd),
            category=rel.category,
            single_source=rel.single_source,
            lead_time_days=rel.lead_time_days,
            confidence=float(rel.confidence),
            source=rel.source,
            valid_from=rel.valid_from,
            valid_to=rel.valid_to,
            created_at=rel.created_at,
            updated_at=rel.updated_at,
        )

    async def get_supplier_detail(
        self, supplier_id: uuid.UUID, org_id: uuid.UUID
    ) -> SupplierDetailOut:
        result = await self.repo.get_supplier_by_id(supplier_id, org_id)
        if not result:
            raise SupplierNotFound(supplier_id)

        rel, comp = result
        comp_detail = await self.company_svc.get_company_detail(comp.id)
        return SupplierDetailOut(
            id=rel.id,
            org_id=rel.org_id,
            company_id=comp.id,
            company=CompanySummaryOut.model_validate(comp),
            company_detail=comp_detail,
            relationship_type=rel.relationship_type,
            tier=rel.tier,
            criticality=rel.criticality,
            annual_spend_usd=_to_float(rel.annual_spend_usd),
            category=rel.category,
            single_source=rel.single_source,
            lead_time_days=rel.lead_time_days,
            confidence=float(rel.confidence),
            source=rel.source,
            valid_from=rel.valid_from,
            valid_to=rel.valid_to,
            created_at=rel.created_at,
            updated_at=rel.updated_at,
        )

    async def create_supplier(
        self, org_id: uuid.UUID, payload: SupplierCreate
    ) -> SupplierOut:
        # Resolve company via ER cascade or ID lookup
        if payload.company_id:
            company = await self.company_repo.get_by_id(payload.company_id)
            if not company:
                raise CompanyNotFound(payload.company_id)
        else:
            assert payload.legal_name is not None
            from app.modules.companies.resolution.cascade import EntityResolutionCascade

            cascade = EntityResolutionCascade(self.db)
            er_res = await cascade.resolve(
                name=payload.legal_name,
                country=payload.country,
                domain=payload.primary_domain,
                org_id=org_id,
                auto_review=True,
            )
            if er_res.matched and er_res.company_id:
                resolved_comp = await self.company_repo.get_by_id(er_res.company_id)
                company = resolved_comp if resolved_comp else await self.company_svc.get_or_create_by_name(
                    legal_name=payload.legal_name,
                    country=payload.country,
                    primary_domain=payload.primary_domain,
                )
            else:
                company = await self.company_svc.get_or_create_by_name(
                    legal_name=payload.legal_name,
                    country=payload.country,
                    primary_domain=payload.primary_domain,
                )

        rel = await self.repo.create_supplier(
            org_id=org_id,
            from_company_id=company.id,
            tier=payload.tier,
            criticality=payload.criticality,
            annual_spend_usd=payload.annual_spend_usd,
            category=payload.category,
            single_source=payload.single_source,
            lead_time_days=payload.lead_time_days,
            confidence=payload.confidence,
            source=payload.source,
        )

        return SupplierOut(
            id=rel.id,
            org_id=rel.org_id,
            company_id=company.id,
            company=CompanySummaryOut.model_validate(company),
            relationship_type=rel.relationship_type,
            tier=rel.tier,
            criticality=rel.criticality,
            annual_spend_usd=_to_float(rel.annual_spend_usd),
            category=rel.category,
            single_source=rel.single_source,
            lead_time_days=rel.lead_time_days,
            confidence=float(rel.confidence),
            source=rel.source,
            valid_from=rel.valid_from,
            valid_to=rel.valid_to,
            created_at=rel.created_at,
            updated_at=rel.updated_at,
        )

    async def update_supplier(
        self,
        supplier_id: uuid.UUID,
        org_id: uuid.UUID,
        payload: SupplierUpdate,
    ) -> SupplierOut:
        updates = payload.model_dump(exclude_unset=True)
        rel = await self.repo.update_supplier(
            supplier_id=supplier_id,
            org_id=org_id,
            **updates,
        )
        if not rel:
            raise SupplierNotFound(supplier_id)

        return await self.get_supplier(supplier_id, org_id)

    async def delete_supplier(
        self, supplier_id: uuid.UUID, org_id: uuid.UUID
    ) -> None:
        deleted = await self.repo.soft_delete_supplier(supplier_id, org_id)
        if not deleted:
            raise SupplierNotFound(supplier_id)

    # ── Generic Relationships ───────────────────────────────────────────────

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
    ) -> tuple[list[RelationshipOut], str | None, bool]:
        rows, next_cursor, has_more = await self.repo.list_relationships(
            org_id=org_id,
            relationship_type=relationship_type,
            from_company_id=from_company_id,
            to_company_id=to_company_id,
            tier=tier,
            active_only=active_only,
            cursor=cursor,
            limit=limit,
        )

        items = [
            RelationshipOut(
                id=rel.id,
                org_id=rel.org_id,
                from_company_id=from_comp.id,
                from_company=CompanySummaryOut.model_validate(from_comp),
                to_company_id=to_comp.id if to_comp else None,
                to_company=CompanySummaryOut.model_validate(to_comp) if to_comp else None,
                to_org_id=rel.to_org_id,
                relationship_type=rel.relationship_type,
                tier=rel.tier,
                criticality=rel.criticality,
                annual_spend_usd=_to_float(rel.annual_spend_usd),
                category=rel.category,
                single_source=rel.single_source,
                lead_time_days=rel.lead_time_days,
                confidence=float(rel.confidence),
                source=rel.source,
                valid_from=rel.valid_from,
                valid_to=rel.valid_to,
                created_at=rel.created_at,
                updated_at=rel.updated_at,
            )
            for rel, from_comp, to_comp in rows
        ]

        return items, next_cursor, has_more

    async def get_relationship(
        self, rel_id: uuid.UUID, org_id: uuid.UUID
    ) -> RelationshipOut:
        result = await self.repo.get_relationship_by_id(rel_id, org_id)
        if not result:
            raise RelationshipNotFound(rel_id)

        rel, from_comp, to_comp = result
        return RelationshipOut(
            id=rel.id,
            org_id=rel.org_id,
            from_company_id=from_comp.id,
            from_company=CompanySummaryOut.model_validate(from_comp),
            to_company_id=to_comp.id if to_comp else None,
            to_company=CompanySummaryOut.model_validate(to_comp) if to_comp else None,
            to_org_id=rel.to_org_id,
            relationship_type=rel.relationship_type,
            tier=rel.tier,
            criticality=rel.criticality,
            annual_spend_usd=_to_float(rel.annual_spend_usd),
            category=rel.category,
            single_source=rel.single_source,
            lead_time_days=rel.lead_time_days,
            confidence=float(rel.confidence),
            source=rel.source,
            valid_from=rel.valid_from,
            valid_to=rel.valid_to,
            created_at=rel.created_at,
            updated_at=rel.updated_at,
        )

    async def create_relationship(
        self, org_id: uuid.UUID, payload: RelationshipCreate
    ) -> RelationshipOut:
        # Verify from_company exists
        from_comp = await self.company_repo.get_by_id(payload.from_company_id)
        if not from_comp:
            raise CompanyNotFound(payload.from_company_id)

        # Verify to_company if given
        to_comp = None
        if payload.to_company_id:
            to_comp = await self.company_repo.get_by_id(payload.to_company_id)
            if not to_comp:
                raise CompanyNotFound(payload.to_company_id)

        to_org_id = payload.to_org_id
        if not to_org_id and not payload.to_company_id:
            to_org_id = org_id

        rel = await self.repo.create_relationship(
            org_id=org_id,
            from_company_id=payload.from_company_id,
            to_company_id=payload.to_company_id,
            to_org_id=to_org_id,
            relationship_type=payload.relationship_type,
            tier=payload.tier,
            criticality=payload.criticality,
            annual_spend_usd=payload.annual_spend_usd,
            category=payload.category,
            single_source=payload.single_source,
            lead_time_days=payload.lead_time_days,
            confidence=payload.confidence,
            source=payload.source,
        )

        return RelationshipOut(
            id=rel.id,
            org_id=rel.org_id,
            from_company_id=from_comp.id,
            from_company=CompanySummaryOut.model_validate(from_comp),
            to_company_id=to_comp.id if to_comp else None,
            to_company=CompanySummaryOut.model_validate(to_comp) if to_comp else None,
            to_org_id=rel.to_org_id,
            relationship_type=rel.relationship_type,
            tier=rel.tier,
            criticality=rel.criticality,
            annual_spend_usd=_to_float(rel.annual_spend_usd),
            category=rel.category,
            single_source=rel.single_source,
            lead_time_days=rel.lead_time_days,
            confidence=float(rel.confidence),
            source=rel.source,
            valid_from=rel.valid_from,
            valid_to=rel.valid_to,
            created_at=rel.created_at,
            updated_at=rel.updated_at,
        )

    async def update_relationship(
        self,
        rel_id: uuid.UUID,
        org_id: uuid.UUID,
        payload: RelationshipUpdate,
    ) -> RelationshipOut:
        updates = payload.model_dump(exclude_unset=True)
        rel = await self.repo.update_relationship(
            rel_id=rel_id,
            org_id=org_id,
            **updates,
        )
        if not rel:
            raise RelationshipNotFound(rel_id)

        return await self.get_relationship(rel_id, org_id)

    async def delete_relationship(
        self, rel_id: uuid.UUID, org_id: uuid.UUID
    ) -> None:
        deleted = await self.repo.soft_delete_relationship(rel_id, org_id)
        if not deleted:
            raise RelationshipNotFound(rel_id)

    # ── Phase 7 Graph Visualizer & Path Finding ──────────────────────────────

    async def get_graph(
        self,
        *,
        org_id: uuid.UUID,
        root: uuid.UUID | None = None,
        depth: int = 3,
        types: list[str] | None = None,
        limit: int = 300,
    ) -> GraphData:
        """
        Builds the Cytoscape-ready node/edge payload for the supply chain graph.
        Includes Organization node, Company nodes (with risk bands), and Location nodes.
        Enforces depth and node caps.
        """
        raw_edges, has_more = await self.repo.traverse_graph(
            org_id=org_id,
            root_id=root,
            max_depth=depth,
            relationship_types=types,
            limit=limit,
        )

        company_ids: set[uuid.UUID] = set()
        for edge in raw_edges:
            company_ids.add(edge["from_company_id"])
            if edge.get("to_company_id"):
                company_ids.add(edge["to_company_id"])

        if root and root not in company_ids:
            company_ids.add(root)

        # Batch load canonical companies, locations, and risk assessments
        companies = await self.repo.get_companies_by_ids(list(company_ids))
        risk_map = await self.repo.get_company_risk_assessments(org_id, list(company_ids))
        org = await self.repo.get_organization(org_id)

        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        # 1. Organization central sink node
        org_node_id = f"org_{org_id}"
        org_label = org.name if org else "Tenant Organization"
        nodes[org_node_id] = GraphNode(
            id=org_node_id,
            entity_id=str(org_id),
            label=org_label,
            type="organization",
            country=org.country if org else None,
            risk_level="LOW",
            metadata={
                "subscription_tier": org.subscription_tier if org else "enterprise",
                "slug": org.slug if org else "org",
            },
        )

        # Pre-index edge attributes for companies
        company_edge_meta: dict[uuid.UUID, dict[str, Any]] = {}
        for edge in raw_edges:
            cid = edge["from_company_id"]
            if cid not in company_edge_meta:
                company_edge_meta[cid] = {
                    "tier": edge.get("tier"),
                    "criticality": edge.get("criticality"),
                    "annual_spend_usd": edge.get("annual_spend_usd"),
                    "category": edge.get("category"),
                    "single_source": edge.get("single_source", False),
                }

        # 2. Company nodes
        for cid in company_ids:
            comp = companies.get(cid)
            comp_node_id = f"comp_{cid}"
            risk_band, risk_score = risk_map.get(cid, ("UNKNOWN", None))
            edge_meta = company_edge_meta.get(cid, {})

            # Derive baseline risk from criticality if no formal event assessment exists
            if risk_band == "UNKNOWN":
                crit = edge_meta.get("criticality")
                if crit == 5:
                    risk_band = "HIGH"
                elif crit == 4:
                    risk_band = "MEDIUM"
                elif crit and crit <= 2:
                    risk_band = "LOW"

            nodes[comp_node_id] = GraphNode(
                id=comp_node_id,
                entity_id=str(cid),
                label=comp.legal_name if comp else f"Supplier {str(cid)[:8]}",
                type="company",
                country=comp.country if comp else None,
                risk_level=risk_band,
                risk_score=risk_score,
                annual_spend_usd=edge_meta.get("annual_spend_usd"),
                criticality=edge_meta.get("criticality"),
                tier=edge_meta.get("tier"),
                category=edge_meta.get("category"),
                single_source=edge_meta.get("single_source", False),
                metadata={
                    "primary_domain": comp.primary_domain if comp else None,
                    "legal_form": comp.legal_form if comp else None,
                    "is_verified": comp.is_verified if comp else False,
                    "data_source": comp.data_source if comp else None,
                },
            )

        # 3. Location nodes (if requested or types is None)
        if types is None or "located_in" in types:
            comp_locs = await self.repo.get_company_locations(list(company_ids))
            for comp_loc, loc in comp_locs:
                loc_node_id = f"loc_{loc.id}"
                loc_label = f"{loc.city or loc.region or 'Site'}, {loc.country}"
                if loc_node_id not in nodes:
                    nodes[loc_node_id] = GraphNode(
                        id=loc_node_id,
                        entity_id=str(loc.id),
                        label=loc_label,
                        type="location",
                        country=loc.country,
                        risk_level="UNKNOWN",
                        metadata={
                            "site_type": comp_loc.site_type or "hq",
                            "city": loc.city,
                            "region": loc.region,
                            "lat": float(loc.lat) if loc.lat is not None else None,
                            "lon": float(loc.lon) if loc.lon is not None else None,
                        },
                    )

                loc_edge_id = f"edge_loc_{comp_loc.id}"
                edges.append(
                    GraphEdge(
                        id=loc_edge_id,
                        source=f"comp_{comp_loc.company_id}",
                        target=loc_node_id,
                        relationship_type="located_in",
                        confidence=float(comp_loc.confidence or 1.0),
                        source_type=comp_loc.source or "gleif",
                    )
                )

        # 4. Supply chain edges
        for raw in raw_edges:
            edge_id = str(raw["edge_id"])
            source_id = f"comp_{raw['from_company_id']}"
            if raw.get("to_company_id"):
                target_id = f"comp_{raw['to_company_id']}"
            else:
                target_id = org_node_id

            edges.append(
                GraphEdge(
                    id=edge_id,
                    source=source_id,
                    target=target_id,
                    relationship_type=raw["relationship_type"],
                    tier=raw.get("tier"),
                    criticality=raw.get("criticality"),
                    annual_spend_usd=raw.get("annual_spend_usd"),
                    confidence=raw.get("confidence", 1.0),
                    source_type=raw.get("source", "user_declared"),
                    single_source=raw.get("single_source", False),
                    lead_time_days=raw.get("lead_time_days"),
                )
            )

        meta = GraphMetadata(
            root_id=str(root) if root else None,
            depth=depth,
            node_count=len(nodes),
            edge_count=len(edges),
            truncated=has_more,
        )

        return GraphData(nodes=list(nodes.values()), edges=edges, meta=meta)

    async def get_paths(
        self,
        *,
        org_id: uuid.UUID,
        from_id: uuid.UUID,
        to_id: uuid.UUID | None = None,
        max_depth: int = 5,
    ) -> GraphPathsResponse:
        """
        Finds exposure paths from an affected upstream company to the tenant org or downstream target.
        Generates deterministic natural language explanations matching the database truth.
        """
        from_comp = await self.company_repo.get_by_id(from_id)
        from_node = (
            GraphNode(
                id=f"comp_{from_id}",
                entity_id=str(from_id),
                label=from_comp.legal_name if from_comp else str(from_id),
                type="company",
                country=from_comp.country if from_comp else None,
            )
            if from_comp
            else None
        )

        to_node: GraphNode | None = None
        org = await self.repo.get_organization(org_id)
        if to_id is None or to_id == org_id:
            to_node = GraphNode(
                id=f"org_{org_id}",
                entity_id=str(org_id),
                label=org.name if org else "Tenant Organization",
                type="organization",
                country=org.country if org else None,
            )
        else:
            to_comp = await self.company_repo.get_by_id(to_id)
            if to_comp:
                to_node = GraphNode(
                    id=f"comp_{to_id}",
                    entity_id=str(to_id),
                    label=to_comp.legal_name,
                    type="company",
                    country=to_comp.country,
                )

        raw_paths = await self.repo.find_paths(
            org_id=org_id,
            from_company_id=from_id,
            to_company_id=to_id,
            max_depth=max_depth,
        )

        from_name = from_comp.legal_name if from_comp else f"Company {str(from_id)[:8]}"
        target_name = to_node.label if to_node else (org.name if org else "Tenant Organization")

        if not raw_paths:
            return GraphPathsResponse(
                from_node=from_node,
                to_node=to_node,
                paths=[],
                summary=f"No exposure path discovered from {from_name} to {target_name} within {max_depth} tiers.",
            )

        # Collect all referenced companies
        path_company_ids: set[uuid.UUID] = set()
        for p in raw_paths:
            for cid in p["path"]:
                path_company_ids.add(cid)
            if p.get("to_company_id"):
                path_company_ids.add(p["to_company_id"])

        companies_map = await self.repo.get_companies_by_ids(list(path_company_ids))

        constructed_paths: list[GraphPath] = []
        for p in raw_paths:
            path_nodes: list[GraphNode] = []
            path_edges: list[GraphEdge] = []

            # Nodes along path
            for cid in p["path"]:
                c = companies_map.get(cid)
                path_nodes.append(
                    GraphNode(
                        id=f"comp_{cid}",
                        entity_id=str(cid),
                        label=c.legal_name if c else str(cid),
                        type="company",
                        country=c.country if c else None,
                    )
                )

            # Final target node
            if p.get("to_company_id"):
                tc = companies_map.get(p["to_company_id"])
                path_nodes.append(
                    GraphNode(
                        id=f"comp_{p['to_company_id']}",
                        entity_id=str(p["to_company_id"]),
                        label=tc.legal_name if tc else str(p["to_company_id"]),
                        type="company",
                        country=tc.country if tc else None,
                    )
                )
            else:
                path_nodes.append(
                    GraphNode(
                        id=f"org_{org_id}",
                        entity_id=str(org_id),
                        label=org.name if org else "Tenant Organization",
                        type="organization",
                    )
                )

            # Primary edge
            path_edges.append(
                GraphEdge(
                    id=str(p["edge_id"]),
                    source=f"comp_{p['from_company_id']}",
                    target=f"comp_{p['to_company_id']}" if p.get("to_company_id") else f"org_{org_id}",
                    relationship_type=p["relationship_type"],
                    tier=p.get("tier"),
                    criticality=p.get("criticality"),
                    annual_spend_usd=p.get("annual_spend_usd"),
                    confidence=p.get("confidence", 1.0),
                    source_type=p.get("source", "user_declared"),
                )
            )

            # Generate deterministic path explanation
            chain_parts: list[str] = []
            for idx, n in enumerate(path_nodes[:-1]):
                next_n = path_nodes[idx + 1]
                chain_parts.append(f"{n.label} -> {next_n.label}")

            spend_detail = ""
            if p.get("annual_spend_usd"):
                spend_detail = f" with ${p['annual_spend_usd']:,.0f} direct annual spend"

            crit_detail = ""
            if p.get("criticality"):
                crit_detail = f" (Criticality: {p['criticality']}/5)"

            explanation = (
                f"Path from {from_name} reaches {target_name} across {p['depth']} tier(s) "
                f"with {p['path_confidence'] * 100:.1f}% cumulative confidence. "
                f"Supply Chain Route: {' -> '.join([n.label for n in path_nodes])}. "
                f"Exposure impacts {target_name}{spend_detail}{crit_detail} via {p['relationship_type']}."
            )

            constructed_paths.append(
                GraphPath(
                    nodes=path_nodes,
                    edges=path_edges,
                    depth=p["depth"],
                    path_confidence=p["path_confidence"],
                    explanation=explanation,
                )
            )

        summary = (
            f"Discovered {len(constructed_paths)} verified supply chain path(s) connecting {from_name} "
            f"to {target_name} across up to {max(p.depth for p in constructed_paths)} tiers. "
            f"Highest path confidence: {constructed_paths[0].path_confidence * 100:.1f}%."
        )

        return GraphPathsResponse(
            from_node=from_node,
            to_node=to_node,
            paths=constructed_paths,
            summary=summary,
        )

