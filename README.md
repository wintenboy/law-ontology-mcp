<p align="center">
  <h1 align="center">law-ontology-mcp</h1>
  <p align="center">
    <strong>법령 온톨로지 MCP 서버</strong>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
    <img src="https://img.shields.io/badge/MCP-compatible-blue" alt="MCP Compatible">
  </p>
</p>

---

법제처 [법령 LOD](https://lod.law.go.kr/) 온톨로지의 SPARQL 엔드포인트를 활용한 법령 검색 [MCP](https://modelcontextprotocol.io/) 서버입니다.

## 설치

```bash
git clone https://github.com/wintenboy/law-ontology-mcp.git
cd law-ontology-mcp
pip install -e .
```

## 설정

MCP 클라이언트 설정 파일에 추가:

```json
{
  "mcpServers": {
    "law-ontology": {
      "command": "law-ontology-mcp"
    }
  }
}
```

| 클라이언트 | 설정 파일 경로 |
|-----------|--------------|
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |
| Cursor | `.cursor/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
| Claude Code | `claude mcp add law-ontology -- law-ontology-mcp` |

## 도구

| 도구 | 설명 |
|------|------|
| `search_law` | 키워드로 법령 검색 |
| `get_law_detail` | 법령 상세 정보 조회 |
| `search_by_agency` | 소관부처별 법령 검색 |
| `search_by_region` | 지역별 자치법규 검색 |
| `get_statistics` | 법령 유형별 통계 |
| `execute_sparql` | SPARQL 쿼리 직접 실행 |
| `list_laws` | 법령 유형별 목록 조회 |
| `visualize_law_network` | 법령 온톨로지 네트워크 시각화 |

## 사용 예시

```
"개인정보보호 관련 법령 검색해줘"
"민법 상세 정보 보여줘"
"국방부 소관 법령 찾아줘"
"서울특별시 자치법규 검색해줘"
"법령 유형별 통계 알려줘"
"법령 온톨로지 네트워크 시각화해줘"
```

## 라이선스

MIT

<!-- mcp-name: io.github.wintenboy/law-ontology-mcp -->
