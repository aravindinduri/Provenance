"""
tests/unit/test_phase7_graph.py — Comprehensive unit tests for Phase 7:
Supply chain topology graph traversal, cycle guard termination, caps enforcement,
performance benchmark, and path explanation matching DB truth.
"""

from __future__ import annotations

import time
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.modules.graph.schemas import (
    GraphData,
    GraphEdge,
    GraphMetadata,
    GraphNode,
    GraphPath,
    GraphPathsResponse,
)
from app.modules.graph.service import GraphService


# ── 1. Schema Validation Tests ────────────────────────────────────────────────

def test_graph_node_schema_defaults_and_validation():
    node = GraphNode(
        id="comp_123",
        entity_id="123",
        label="Acme Microelectronics",
        type="company",
        country="US",
        risk_level="HIGH",
        risk_score=78.5,
        annual_spend_usd=1200000.0,
        criticality=4,
        tier=1,
        single_source=True,
    )
    assert node.id == "comp_123"
    assert node.risk_level == "HIGH"
    assert node.criticality == 4
    assert node.single_source is True

    # Criticality out of bounds (1-5)
    with pytest.raises(ValidationError):
        GraphNode(id="comp_bad", label="Bad", criticality=6)


def test_graph_edge_schema_confidence_bounds():
    edge = GraphEdge(
        id="edge_1",
        source="comp_a",
        target="comp_b",
        relationship_type="sub_supplies_to",
        tier=2,
        confidence=0.95,
        source_type="user_declared",
    )
    assert edge.confidence == 0.95
    assert edge.relationship_type == "sub_supplies_to"

    # Confidence must be between 0.0 and 1.0
    with pytest.raises(ValidationError):
        GraphEdge(
            id="edge_bad",
            source="a",
            target="b",
            relationship_type="supplies_to",
            confidence=1.5,
        )


def test_graph_metadata_depth_bounds():
    meta = GraphMetadata(root_id="comp_1", depth=3, node_count=15, edge_count=14)
    assert meta.depth == 3
    assert meta.truncated is False

    with pytest.raises(ValidationError):
        GraphMetadata(depth=0)

    with pytest.raises(ValidationError):
        GraphMetadata(depth=6)


def test_graph_data_container():
    node_a = GraphNode(id="comp_a", label="A", type="company")
    node_b = GraphNode(id="org_1", label="Org", type="organization")
    edge = GraphEdge(id="e1", source="comp_a", target="org_1", relationship_type="supplies_to")
    meta = GraphMetadata(depth=1, node_count=2, edge_count=1)

    data = GraphData(nodes=[node_a, node_b], edges=[edge], meta=meta)
    assert len(data.nodes) == 2
    assert len(data.edges) == 1
    assert data.meta.node_count == 2


# ── 2. Cycle Guard & Traversal Termination (A -> B -> C -> A) ─────────────────

@pytest.mark.asyncio
async def test_cycle_guard_terminates_cleanly():
    """
    Arch §8 & Phase 7 acceptance requirement:
    Given cyclic edges A -> B -> C -> A in the supply graph,
    traversal must terminate without infinite loop and return valid unique edges.
    """
    org_id = uuid.uuid4()
    comp_a = uuid.uuid4()
    comp_b = uuid.uuid4()
    comp_c = uuid.uuid4()

    # Create mock relationships simulating a cycle:
    # A supplies to B, B supplies to C, C supplies to A, and A supplies to Org
    from app.modules.graph.models import SupplierRelationship
    from app.modules.graph.repository import GraphRepository

    mock_rels = [
        SupplierRelationship(
            id=uuid.uuid4(),
            org_id=org_id,
            from_company_id=comp_a,
            to_company_id=comp_b,
            relationship_type="sub_supplies_to",
            confidence=0.9,
            valid_from=date.today(),
            valid_to=None,
            deleted_at=None,
        ),
        SupplierRelationship(
            id=uuid.uuid4(),
            org_id=org_id,
            from_company_id=comp_b,
            to_company_id=comp_c,
            relationship_type="sub_supplies_to",
            confidence=0.9,
            valid_from=date.today(),
            valid_to=None,
            deleted_at=None,
        ),
        SupplierRelationship(
            id=uuid.uuid4(),
            org_id=org_id,
            from_company_id=comp_c,
            to_company_id=comp_a,
            relationship_type="sub_supplies_to",
            confidence=0.9,
            valid_from=date.today(),
            valid_to=None,
            deleted_at=None,
        ),
        SupplierRelationship(
            id=uuid.uuid4(),
            org_id=org_id,
            from_company_id=comp_a,
            to_org_id=org_id,
            relationship_type="supplies_to",
            tier=1,
            confidence=1.0,
            valid_from=date.today(),
            valid_to=None,
            deleted_at=None,
        ),
    ]

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_rels
    mock_db.execute.return_value = mock_result

    repo = GraphRepository(mock_db)

    # In-memory traversal with cycle guard
    edges, has_more = await repo._in_memory_traverse(
        org_id=org_id,
        root_id=None,
        max_depth=5,
        relationship_types=None,
        limit=300,
    )

    # Cycle MUST terminate and return visited unique edges
    assert len(edges) <= 4
    assert has_more is False
    edge_ids = [e["edge_id"] for e in edges]
    assert len(edge_ids) == len(set(edge_ids))  # all unique


# ── 3. Path Finding & Confidence Product Math ────────────────────────────────

@pytest.mark.asyncio
async def test_path_finding_confidence_product_and_cycle_guard():
    """
    Verifies that multi-hop paths accurately multiply edge confidences:
    Path confidence = conf(hop1) * conf(hop2) * conf(hop3).
    Also asserts cycle A -> B -> A terminates.
    """
    org_id = uuid.uuid4()
    tier3_comp = uuid.uuid4()
    tier2_comp = uuid.uuid4()
    tier1_comp = uuid.uuid4()

    from app.modules.graph.models import SupplierRelationship
    from app.modules.graph.repository import GraphRepository

    mock_rels = [
        SupplierRelationship(
            id=uuid.uuid4(),
            org_id=org_id,
            from_company_id=tier3_comp,
            to_company_id=tier2_comp,
            relationship_type="sub_supplies_to",
            tier=3,
            confidence=0.90,
            valid_from=date.today(),
            valid_to=None,
            deleted_at=None,
        ),
        SupplierRelationship(
            id=uuid.uuid4(),
            org_id=org_id,
            from_company_id=tier2_comp,
            to_company_id=tier1_comp,
            relationship_type="sub_supplies_to",
            tier=2,
            confidence=0.95,
            valid_from=date.today(),
            valid_to=None,
            deleted_at=None,
        ),
        SupplierRelationship(
            id=uuid.uuid4(),
            org_id=org_id,
            from_company_id=tier1_comp,
            to_org_id=org_id,
            relationship_type="supplies_to",
            tier=1,
            criticality=4,
            annual_spend_usd=2500000.0,
            confidence=1.0,
            valid_from=date.today(),
            valid_to=None,
            deleted_at=None,
        ),
        # Loopback edge to test cycle guard: tier2 -> tier3
        SupplierRelationship(
            id=uuid.uuid4(),
            org_id=org_id,
            from_company_id=tier2_comp,
            to_company_id=tier3_comp,
            relationship_type="sub_supplies_to",
            confidence=0.5,
            valid_from=date.today(),
            valid_to=None,
            deleted_at=None,
        ),
    ]

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_rels
    mock_db.execute.return_value = mock_result

    repo = GraphRepository(mock_db)

    paths = await repo._in_memory_find_paths(
        org_id=org_id,
        from_company_id=tier3_comp,
        to_company_id=None,  # targets tenant org
        max_depth=5,
        limit=10,
    )

    assert len(paths) == 1
    p = paths[0]
    assert p["depth"] == 3
    # Expected confidence: 0.90 * 0.95 * 1.0 = 0.855
    expected_conf = round(0.90 * 0.95 * 1.0, 4)
    assert p["path_confidence"] == expected_conf


# ── 4. Depth Capping (1 to 5) ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_depth_capping_enforced():
    """Verify that traversal does not exceed requested max_depth."""
    org_id = uuid.uuid4()
    chain = [uuid.uuid4() for _ in range(7)]

    from app.modules.graph.models import SupplierRelationship
    from app.modules.graph.repository import GraphRepository

    mock_rels = []
    # Build linear chain: 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> Org
    for i in range(5):
        mock_rels.append(
            SupplierRelationship(
                id=uuid.uuid4(),
                org_id=org_id,
                from_company_id=chain[i + 1],
                to_company_id=chain[i],
                relationship_type="sub_supplies_to",
                tier=i + 2,
                confidence=1.0,
                valid_from=date.today(),
                valid_to=None,
                deleted_at=None,
            )
        )
    mock_rels.append(
        SupplierRelationship(
            id=uuid.uuid4(),
            org_id=org_id,
            from_company_id=chain[0],
            to_org_id=org_id,
            relationship_type="supplies_to",
            tier=1,
            confidence=1.0,
            valid_from=date.today(),
            valid_to=None,
            deleted_at=None,
        )
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_rels
    mock_db.execute.return_value = mock_result

    repo = GraphRepository(mock_db)

    # Test depth 2
    edges_d2, _ = await repo._in_memory_traverse(
        org_id=org_id, root_id=None, max_depth=2, relationship_types=None, limit=300
    )
    assert all(e["depth"] <= 2 for e in edges_d2)

    # Test depth 4
    edges_d4, _ = await repo._in_memory_traverse(
        org_id=org_id, root_id=None, max_depth=4, relationship_types=None, limit=300
    )
    assert all(e["depth"] <= 4 for e in edges_d4)


# ── 5. Performance Benchmark (2,000 nodes traversal <200 ms) ──────────────────

@pytest.mark.asyncio
async def test_traversal_performance_at_2000_nodes():
    """
    Phase 7 acceptance criterion:
    "Accept: traversal p95 <200 ms on the 2k-supplier seed; graph renders 300 nodes smoothly"
    """
    org_id = uuid.uuid4()
    from app.modules.graph.models import SupplierRelationship
    from app.modules.graph.repository import GraphRepository

    # Synthesize 2,000 relationships across 3 tiers
    num_nodes = 2000
    companies = [uuid.uuid4() for _ in range(num_nodes)]
    mock_rels: list[SupplierRelationship] = []

    # 200 direct suppliers to org
    for i in range(200):
        mock_rels.append(
            SupplierRelationship(
                id=uuid.uuid4(),
                org_id=org_id,
                from_company_id=companies[i],
                to_org_id=org_id,
                relationship_type="supplies_to",
                tier=1,
                confidence=1.0,
                valid_from=date.today(),
                valid_to=None,
                deleted_at=None,
            )
        )

    # 800 tier-2 suppliers supplying the 200 tier-1 suppliers
    for i in range(200, 1000):
        target_t1 = companies[i % 200]
        mock_rels.append(
            SupplierRelationship(
                id=uuid.uuid4(),
                org_id=org_id,
                from_company_id=companies[i],
                to_company_id=target_t1,
                relationship_type="sub_supplies_to",
                tier=2,
                confidence=0.9,
                valid_from=date.today(),
                valid_to=None,
                deleted_at=None,
            )
        )

    # 1,000 tier-3 suppliers supplying the 800 tier-2 suppliers
    for i in range(1000, 2000):
        target_t2 = companies[200 + (i % 800)]
        mock_rels.append(
            SupplierRelationship(
                id=uuid.uuid4(),
                org_id=org_id,
                from_company_id=companies[i],
                to_company_id=target_t2,
                relationship_type="sub_supplies_to",
                tier=3,
                confidence=0.85,
                valid_from=date.today(),
                valid_to=None,
                deleted_at=None,
            )
        )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_rels
    mock_db.execute.return_value = mock_result

    repo = GraphRepository(mock_db)

    # Benchmark traversal at depth 3 with limit 300
    start_time = time.perf_counter()
    edges, _ = await repo._in_memory_traverse(
        org_id=org_id,
        root_id=None,
        max_depth=3,
        relationship_types=None,
        limit=300,
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert len(edges) <= 300
    # Strict latency check: must be well under 200ms
    assert elapsed_ms < 200, f"Traversal took {elapsed_ms:.2f}ms, exceeding 200ms target"


# ── 6. Path Explanation Matches DB Truth ──────────────────────────────────────

@pytest.mark.asyncio
async def test_path_explanation_matches_db_truth():
    """
    Arch Phase 7 acceptance criterion:
    "path explanation matches DB truth."
    Verifies that the generated explanation includes exact company names,
    criticality, annual spend, and confidence.
    """
    org_id = uuid.uuid4()
    comp_a_id = uuid.uuid4()
    comp_b_id = uuid.uuid4()

    mock_db = AsyncMock()
    service = GraphService(mock_db)

    # Mock company lookups
    from app.modules.companies.models import Company
    from app.modules.organizations.models import Organization

    mock_company_a = Company(
        id=comp_a_id,
        legal_name="Apex Rare Earths Ltd",
        name_norm="apex rare earths ltd",
        country="AU",
    )
    mock_company_b = Company(
        id=comp_b_id,
        legal_name="Pacific Magnetics Fab",
        name_norm="pacific magnetics fab",
        country="JP",
    )
    mock_org = Organization(
        id=org_id,
        clerk_org_id="clerk_test",
        name="Apex Turbine Dynamics",
        slug="apex-turbines",
    )

    service.company_repo.get_by_id = AsyncMock(side_effect=lambda cid: mock_company_a if cid == comp_a_id else (mock_company_b if cid == comp_b_id else None))
    service.repo.get_organization = AsyncMock(return_value=mock_org)
    service.repo.get_companies_by_ids = AsyncMock(return_value={comp_a_id: mock_company_a, comp_b_id: mock_company_b})

    # Mock raw path returned from repo
    mock_path_record = {
        "edge_id": uuid.uuid4(),
        "from_company_id": comp_a_id,
        "to_company_id": None,
        "to_org_id": org_id,
        "relationship_type": "supplies_to",
        "tier": 1,
        "criticality": 5,
        "annual_spend_usd": 3800000.0,
        "confidence": 0.98,
        "depth": 1,
        "path": [comp_a_id],
        "edge_path": [uuid.uuid4()],
        "path_confidence": 0.98,
    }
    service.repo.find_paths = AsyncMock(return_value=[mock_path_record])

    result: GraphPathsResponse = await service.get_paths(
        org_id=org_id,
        from_id=comp_a_id,
        to_id=None,
    )

    assert len(result.paths) == 1
    path = result.paths[0]
    assert path.path_confidence == 0.98
    assert "Apex Rare Earths Ltd" in path.explanation
    assert "Apex Turbine Dynamics" in path.explanation
    assert "$3,800,000" in path.explanation
    assert "Criticality: 5/5" in path.explanation
    assert "98.0%" in path.explanation
