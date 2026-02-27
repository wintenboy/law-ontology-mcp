"""Integration tests for Law Ontology MCP client."""

import asyncio
import time
import sys

sys.path.insert(0, "src")

from law_ontology_mcp.sparql_client import LawOntologyClient
from law_ontology_mcp.queries import (
    list_laws_query,
    get_law_by_id_query,
    search_by_agency_code_query,
    search_by_region_code_query,
    get_statistics_by_type_query,
    get_all_statistics_query,
    AGENCY_CODES,
    REGION_CODES,
)


async def test_sparql_basic():
    """Test basic SPARQL query."""
    c = LawOntologyClient()
    try:
        query = list_laws_query(limit=5)
        start = time.time()
        results = await c.sparql(query)
        elapsed = time.time() - start
        print(f"[PASS] SPARQL basic: {len(results)} results in {elapsed:.3f}s")
        for r in results:
            print(f"  {r}")
        assert len(results) > 0
    finally:
        await c.close()


async def test_sparql_agency():
    """Test SPARQL agency search."""
    c = LawOntologyClient()
    try:
        code = AGENCY_CODES["국방부"]
        query = search_by_agency_code_query(code, limit=5)
        start = time.time()
        results = await c.sparql(query)
        elapsed = time.time() - start
        print(f"\n[PASS] SPARQL agency (국방부): {len(results)} results in {elapsed:.3f}s")
        for r in results:
            print(f"  {r}")
        assert len(results) > 0
    finally:
        await c.close()


async def test_sparql_region():
    """Test SPARQL region search."""
    c = LawOntologyClient()
    try:
        code = REGION_CODES["서울특별시"]
        query = search_by_region_code_query(code, limit=5)
        start = time.time()
        results = await c.sparql(query)
        elapsed = time.time() - start
        print(f"\n[PASS] SPARQL region (서울특별시): {len(results)} results in {elapsed:.3f}s")
        for r in results:
            print(f"  {r}")
        assert len(results) > 0
    finally:
        await c.close()


async def test_sparql_statistics():
    """Test statistics query."""
    c = LawOntologyClient()
    try:
        query = get_statistics_by_type_query("법령")
        start = time.time()
        results = await c.sparql(query)
        elapsed = time.time() - start
        print(f"\n[PASS] Statistics (법령): {results} in {elapsed:.3f}s")
        assert len(results) > 0
    finally:
        await c.close()


async def test_search_api():
    """Test keyword search via getSearch.do."""
    c = LawOntologyClient()
    try:
        start = time.time()
        results = await c.search("도로교통", limit=5)
        elapsed = time.time() - start
        print(f"\n[PASS] Search API '도로교통': {len(results)} results in {elapsed:.3f}s")
        for r in results:
            print(f"  label: {r.get('label', '')[:60]}")
            print(f"  uri: {r.get('uri', '')}")
            print(f"  type: {r.get('type', '')}")
            print()
        assert len(results) > 0
    finally:
        await c.close()


async def test_search_with_type():
    """Test search with type filter."""
    c = LawOntologyClient()
    try:
        start = time.time()
        results = await c.search("민법", law_type="현행법령", limit=5)
        elapsed = time.time() - start
        print(f"\n[PASS] Search '민법' (현행법령): {len(results)} results in {elapsed:.3f}s")
        for r in results:
            print(f"  {r.get('label', '')[:60]} [{r.get('type', '')}]")
        assert len(results) > 0
    finally:
        await c.close()


async def test_detail():
    """Test detail page retrieval."""
    c = LawOntologyClient()
    try:
        # First search to get a resource ID
        results = await c.search("도로교통법", law_type="현행법령", limit=1)
        if results:
            uri = results[0].get("uri", "")
            resource_id = uri.split("/")[-1] if "/" in uri else uri
            print(f"\n  Testing detail for: {resource_id}")

            start = time.time()
            detail = await c.get_detail(resource_id)
            elapsed = time.time() - start
            print(f"[PASS] Detail ({resource_id}): {len(detail)} properties in {elapsed:.3f}s")
            for d in detail[:10]:
                print(f"  {d['property']}: {d['value'][:80]}")
        else:
            print("\n[SKIP] Detail: no search results to test with")
    finally:
        await c.close()


async def test_cache():
    """Test that caching speeds up repeated queries."""
    c = LawOntologyClient()
    try:
        start = time.time()
        r1 = await c.search("개인정보", limit=3)
        t1 = time.time() - start

        start = time.time()
        r2 = await c.search("개인정보", limit=3)
        t2 = time.time() - start

        print(f"\n[PASS] Cache test:")
        print(f"  First: {t1:.3f}s ({len(r1)} results)")
        print(f"  Cached: {t2:.6f}s ({len(r2)} results)")
        if t1 > 0:
            print(f"  Speedup: {t1/max(t2, 0.000001):.0f}x")
        assert r1 == r2
    finally:
        await c.close()


async def test_ontology_graph():
    """Test ontology graph data building."""
    from law_ontology_mcp.visualization import build_ontology_graph

    c = LawOntologyClient()
    try:
        start = time.time()
        graph = await build_ontology_graph(c)
        elapsed = time.time() - start
        print(f"\n[PASS] Ontology graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges in {elapsed:.1f}s")
        assert len(graph['nodes']) > 0, "No ontology nodes"
        assert len(graph['edges']) > 0, "No ontology edges"
    finally:
        await c.close()


async def test_law_network_graph():
    """Test law network graph data building."""
    from law_ontology_mcp.visualization import build_law_network_graph

    c = LawOntologyClient()
    try:
        start = time.time()
        graph = await build_law_network_graph(c, "\ubbfc\ubc95", limit=3)
        elapsed = time.time() - start
        print(f"\n[PASS] Law network: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges in {elapsed:.1f}s")
        assert len(graph['nodes']) > 0, "No law nodes"
    finally:
        await c.close()


async def test_html_generation():
    """Test HTML file generation."""
    from law_ontology_mcp.visualization import build_ontology_graph, generate_html
    import os

    c = LawOntologyClient()
    try:
        onto = await build_ontology_graph(c)
        path = generate_html(onto)
        size = os.path.getsize(path)
        print(f"\n[PASS] HTML generation: {path} ({size:,} bytes)")
        assert os.path.exists(path)
        assert size > 1000
        os.unlink(path)
    finally:
        await c.close()


async def main():
    print("=" * 60)
    print("Law Ontology MCP - Integration Tests")
    print("=" * 60)

    tests = [
        test_sparql_basic,
        test_sparql_agency,
        test_sparql_region,
        test_sparql_statistics,
        test_search_api,
        test_search_with_type,
        test_detail,
        test_cache,
        test_ontology_graph,
        test_law_network_graph,
        test_html_generation,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"\n[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
