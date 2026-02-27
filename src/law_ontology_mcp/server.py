"""Law Ontology MCP Server - 법령 온톨로지 기반 법령 검색."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from fastmcp import FastMCP
from fastmcp.server.context import Context

from .sparql_client import LawOntologyClient
from .queries import (
    list_laws_query,
    get_law_by_id_query,
    search_by_agency_code_query,
    search_by_region_code_query,
    get_statistics_by_type_query,
    get_all_statistics_query,
    AGENCY_CODES,
    REGION_CODES,
)
from .prefixes import DEFAULT_PREFIX_BLOCK
from .visualization import (
    build_ontology_graph,
    build_law_network_graph,
    generate_html,
    open_in_browser,
)

AgencyName = Literal[
    "기획재정부", "교육부", "과학기술정보통신부", "외교부", "통일부",
    "법무부", "국방부", "행정안전부", "문화체육관광부", "농림축산식품부",
    "산업통상자원부", "보건복지부", "기후에너지환경부", "고용노동부",
    "국토교통부", "해양수산부", "중소벤처기업부", "국가보훈부",
]

RegionName = Literal[
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
    "충청북도", "충청남도", "전북특별자치도", "전라남도", "경상북도",
    "경상남도", "제주특별자치도",
]

LawType = Literal["전체", "현행법령", "자치법규", "행정규칙", "판례", "조약", "학칙공단", "위원회결정문"]
StatType = Literal["법령", "자치법규", "행정규칙", "판례", "조약", "학칙"]
AgencyLawType = Literal["법령", "행정규칙"]


def _fmt(results: list[dict[str, str]], title: str = "") -> str:
    if not results:
        return f"{title}\n결과가 없습니다." if title else "결과가 없습니다."

    lines = []
    if title:
        lines.append(f"## {title}")
        lines.append(f"총 {len(results)}건\n")

    for i, row in enumerate(results, 1):
        lines.append(f"### {i}.")
        for key, value in row.items():
            if value.startswith("http://lod.law.go.kr/"):
                value = value.replace("http://lod.law.go.kr/", "lod:")
            lines.append(f"- **{key}**: {value}")
        lines.append("")

    return "\n".join(lines)


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    client = LawOntologyClient()
    try:
        yield {"client": client}
    finally:
        await client.close()


mcp = FastMCP("law-ontology-mcp", lifespan=app_lifespan)


@mcp.tool
async def search_law(
    keyword: str,
    type: LawType | None = None,
    agency: str | None = None,
    limit: int = 10,
    ctx: Context = None,
) -> str:
    """법령을 키워드로 검색합니다. 법령명, 조문 내용 등에서 키워드를 찾습니다. 현행법령, 자치법규, 행정규칙, 판례, 조약 등 모든 유형을 검색할 수 있습니다."""
    client: LawOntologyClient = ctx.lifespan_context["client"]
    results = await client.search(
        keyword, law_type=type or "", agency=agency or "", limit=min(limit, 30),
    )
    return _fmt(results, f"법령 검색: '{keyword}'")


@mcp.tool
async def get_law_detail(resource_id: str, ctx: Context = None) -> str:
    """특정 법령의 상세 정보를 조회합니다. 법령 리소스 ID(예: LSI259471, SCPB2200000130717)를 사용합니다. search_law 결과의 URI에서 ID를 추출할 수 있습니다."""
    client: LawOntologyClient = ctx.lifespan_context["client"]
    resource_id = resource_id.replace("http://lod.law.go.kr/resource/", "")
    resource_id = resource_id.replace("lod:resource/", "")

    results = await client.get_detail(resource_id)

    if results:
        grouped: dict[str, list[str]] = {}
        for row in results:
            prop = row.get("property", "")
            val = row.get("value", "")
            if prop not in grouped:
                grouped[prop] = []
            grouped[prop].append(val)

        lines = [f"## 법령 상세: {resource_id}\n"]
        for prop, values in grouped.items():
            if len(values) == 1:
                lines.append(f"- **{prop}**: {values[0]}")
            else:
                lines.append(f"- **{prop}**:")
                for v in values[:10]:
                    lines.append(f"  - {v}")
                if len(values) > 10:
                    lines.append(f"  - ... 외 {len(values) - 10}건")
        return "\n".join(lines)

    query = get_law_by_id_query(resource_id)
    results = await client.sparql(query)
    return _fmt(results, f"법령 상세: {resource_id}")


@mcp.tool
async def search_by_agency(
    agency_name: AgencyName,
    type: AgencyLawType | None = None,
    limit: int = 10,
    ctx: Context = None,
) -> str:
    """소관부처별 법령을 검색합니다."""
    client: LawOntologyClient = ctx.lifespan_context["client"]
    code = AGENCY_CODES.get(agency_name)
    if not code:
        return f"알 수 없는 부처: {agency_name}\n사용 가능: {', '.join(AGENCY_CODES.keys())}"

    query = search_by_agency_code_query(code, type, min(limit, 100))
    results = await client.sparql(query)
    return _fmt(results, f"소관부처별 검색: '{agency_name}'")


@mcp.tool
async def search_by_region(
    region_name: RegionName,
    limit: int = 10,
    ctx: Context = None,
) -> str:
    """지역별 자치법규를 검색합니다."""
    client: LawOntologyClient = ctx.lifespan_context["client"]
    code = REGION_CODES.get(region_name)
    if not code:
        return f"알 수 없는 지역: {region_name}\n사용 가능: {', '.join(REGION_CODES.keys())}"

    query = search_by_region_code_query(code, min(limit, 100))
    results = await client.sparql(query)
    return _fmt(results, f"지역별 자치법규: '{region_name}'")


@mcp.tool
async def get_statistics(
    type: StatType | None = None,
    ctx: Context = None,
) -> str:
    """법령 데이터 통계를 조회합니다."""
    client: LawOntologyClient = ctx.lifespan_context["client"]
    if type:
        query = get_statistics_by_type_query(type)
        results = await client.sparql(query)
        count = results[0].get("count", "0") if results else "0"
        return f"## {type} 통계\n총 {count}건"

    query = get_all_statistics_query()
    results = await client.sparql(query)
    return _fmt(results, "법령 유형별 통계")


@mcp.tool
async def execute_sparql(
    query: str,
    include_prefixes: bool = True,
    ctx: Context = None,
) -> str:
    """SPARQL 쿼리를 직접 실행합니다. PREFIX는 자동 추가됩니다. 주의: FILTER에서 contains(), str(), regex(), lang() 등 문자열 함수는 서버에서 지원하지 않습니다. URI 비교만 가능합니다."""
    client: LawOntologyClient = ctx.lifespan_context["client"]
    if include_prefixes and not query.strip().upper().startswith("PREFIX"):
        query = f"{DEFAULT_PREFIX_BLOCK}\n{query}"

    results = await client.sparql(query)
    return _fmt(results, "SPARQL 쿼리 결과")


@mcp.tool
async def list_laws(
    type: StatType | None = None,
    limit: int = 10,
    ctx: Context = None,
) -> str:
    """법령 유형별 목록을 조회합니다. 키워드 검색 없이 유형별 법령 목록을 가져옵니다."""
    client: LawOntologyClient = ctx.lifespan_context["client"]
    query = list_laws_query(type, min(limit, 100))
    results = await client.sparql(query)
    type_label = type or "현행법령"
    return _fmt(results, f"{type_label} 목록")


@mcp.tool
async def visualize_law_network(
    keyword: str | None = None,
    limit: int = 10,
    output_path: str | None = None,
    open_browser: bool = True,
    ctx: Context = None,
) -> str:
    """법령 온톨로지 네트워크를 시각화합니다. 온톨로지 스키마(클래스/프로퍼티 관계)와 법령 간 관계 네트워크를 인터랙티브 HTML로 생성합니다. 키워드를 입력하면 검색된 법령의 관계 네트워크도 함께 표시됩니다."""
    client: LawOntologyClient = ctx.lifespan_context["client"]

    ontology_data = await build_ontology_graph(client)

    law_data = None
    if keyword:
        law_data = await build_law_network_graph(client, keyword, limit=min(limit, 20))

    file_path = generate_html(ontology_data, law_data, output_path)

    if open_browser:
        open_in_browser(file_path)

    onto_nodes = len(ontology_data.get("nodes", []))
    onto_edges = len(ontology_data.get("edges", []))
    lines = [
        f"## 온톨로지 네트워크 시각화 생성 완료\n",
        f"- **파일**: {file_path}",
        f"- **온톨로지 스키마**: {onto_nodes}개 노드, {onto_edges}개 엣지",
    ]
    if law_data:
        law_nodes = len(law_data.get("nodes", []))
        law_edges = len(law_data.get("edges", []))
        lines.append(f"- **법령 네트워크** ('{keyword}'): {law_nodes}개 노드, {law_edges}개 엣지")
    if open_browser:
        lines.append(f"\n브라우저에서 열렸습니다.")
    return "\n".join(lines)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
