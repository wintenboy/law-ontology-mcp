"""Pre-optimized SPARQL query templates.

IMPORTANT: The LOD SPARQL endpoint does NOT support string functions
(contains, str, regex, lang) in FILTER clauses. Only URI comparisons work.
For keyword text search, use the search API (getSearch.do) instead.
"""

from __future__ import annotations

from .prefixes import DEFAULT_PREFIX_BLOCK, LAW_TYPE_MAP


def list_laws_query(law_type: str | None = None, limit: int = 10) -> str:
    """List laws of a given type."""
    if law_type and law_type in LAW_TYPE_MAP:
        cls = LAW_TYPE_MAP[law_type]
        return f"""{DEFAULT_PREFIX_BLOCK}
SELECT DISTINCT ?law ?lawName WHERE {{
  ?law a {cls} .
  ?law rdfs:label ?lawName
}} ORDER BY ?lawName LIMIT {limit}"""

    return f"""{DEFAULT_PREFIX_BLOCK}
SELECT DISTINCT ?law ?lawName WHERE {{
  ?law a ldc:KoreanLegislation .
  ?law rdfs:label ?lawName
}} ORDER BY ?lawName LIMIT {limit}"""


def get_law_by_uri_query(resource_uri: str) -> str:
    """Get all properties of a specific law resource by full URI."""
    return f"""{DEFAULT_PREFIX_BLOCK}
SELECT DISTINCT ?property ?value WHERE {{
  <{resource_uri}> ?property ?value .
}} LIMIT 200"""


def get_law_by_id_query(resource_id: str) -> str:
    """Get all properties of a law resource by ID (e.g., LSI259471)."""
    return f"""{DEFAULT_PREFIX_BLOCK}
SELECT DISTINCT ?property ?value WHERE {{
  ldr:{resource_id} ?property ?value .
}} LIMIT 200"""


def search_by_agency_code_query(agency_code: str, law_type: str | None = None, limit: int = 10) -> str:
    """Search laws by agency classification code."""
    type_filter = ""
    if law_type and law_type in LAW_TYPE_MAP:
        cls = LAW_TYPE_MAP[law_type]
        type_filter = f"FILTER(?lawType = {cls})"

    return f"""{DEFAULT_PREFIX_BLOCK}
SELECT DISTINCT ?law ?lawName ?lawType WHERE {{
  ?law ldp:hasKoreanAdminAgencyCategory ldr:koreanAdminAgencyClassification_{agency_code} .
  ?law ldp:lawName ?lawName .
  ?law a ?lawType .
  FILTER(?lawType != ldc:KoreanLegislationNorms)
  {type_filter}
}} LIMIT {limit}"""


def search_by_region_code_query(region_code: str, limit: int = 10) -> str:
    """Search ordinances by local government code."""
    return f"""{DEFAULT_PREFIX_BLOCK}
SELECT DISTINCT ?law ?lawName ?announceDate WHERE {{
  ?law ldp:hasKoreanLocalGovernmentCategory ldr:koreanLocalGovernmentClassification_{region_code} .
  ?law ldp:lawName ?lawName .
  OPTIONAL {{ ?law ldp:announceDate ?announceDate }}
}} LIMIT {limit}"""


def get_statistics_by_type_query(law_type: str) -> str:
    """Count laws of a specific type."""
    cls = LAW_TYPE_MAP.get(law_type, "ldc:KoreanLegislation")
    return f"""{DEFAULT_PREFIX_BLOCK}
SELECT (COUNT(DISTINCT ?law) AS ?count) WHERE {{
  ?law a {cls} .
}}"""


def get_ontology_classes_query() -> str:
    """Get all OWL classes with labels from the LOD ontology."""
    return f"""{DEFAULT_PREFIX_BLOCK}
SELECT DISTINCT ?class ?label WHERE {{
  ?class a owl:Class .
  OPTIONAL {{ ?class rdfs:label ?label }}
}} LIMIT 100"""


def get_ontology_object_properties_query() -> str:
    """Get all object properties with domain and range."""
    return f"""{DEFAULT_PREFIX_BLOCK}
SELECT DISTINCT ?prop ?label ?domain ?range WHERE {{
  ?prop a owl:ObjectProperty .
  OPTIONAL {{ ?prop rdfs:label ?label }}
  OPTIONAL {{ ?prop rdfs:domain ?domain }}
  OPTIONAL {{ ?prop rdfs:range ?range }}
}} LIMIT 200"""


def get_ontology_data_properties_query() -> str:
    """Get all data properties with domain."""
    return f"""{DEFAULT_PREFIX_BLOCK}
SELECT DISTINCT ?prop ?label ?domain WHERE {{
  ?prop a owl:DatatypeProperty .
  OPTIONAL {{ ?prop rdfs:label ?label }}
  OPTIONAL {{ ?prop rdfs:domain ?domain }}
}} LIMIT 500"""


def get_subclass_relations_query() -> str:
    """Get class hierarchy (subClassOf relationships)."""
    return f"""{DEFAULT_PREFIX_BLOCK}
SELECT DISTINCT ?sub ?super WHERE {{
  ?sub rdfs:subClassOf ?super .
  ?sub a owl:Class .
  ?super a owl:Class .
}} LIMIT 100"""


def get_all_statistics_query() -> str:
    """Get count for each major law type."""
    return f"""{DEFAULT_PREFIX_BLOCK}
SELECT ?typeName (COUNT(DISTINCT ?law) AS ?count) WHERE {{
  ?law a ?type .
  ?type rdfs:label ?typeName .
  FILTER(?type != ldc:KoreanLegislationNorms)
  FILTER(?type != owl:Thing)
  FILTER(?type != owl:Nothing)
}} GROUP BY ?type ?typeName ORDER BY DESC(?count)"""


# Known agency codes for common Korean government agencies
AGENCY_CODES = {
    "기획재정부": "1051000",
    "교육부": "1341000",
    "과학기술정보통신부": "1371000",
    "외교부": "1261000",
    "통일부": "1311000",
    "법무부": "1270000",
    "국방부": "1290000",
    "행정안전부": "1741000",
    "문화체육관광부": "1390000",
    "농림축산식품부": "1430000",
    "산업통상자원부": "1450000",
    "보건복지부": "1352000",
    "기후에너지환경부": "1480000",
    "고용노동부": "1492000",
    "국토교통부": "1613000",
    "해양수산부": "1463000",
    "중소벤처기업부": "1661000",
    "국가보훈부": "1312000",
}

# Known region codes for Korean local governments
REGION_CODES = {
    "서울특별시": "6110000",
    "부산광역시": "6260000",
    "대구광역시": "6270000",
    "인천광역시": "6280000",
    "광주광역시": "6290000",
    "대전광역시": "6300000",
    "울산광역시": "7480000",
    "세종특별자치시": "6430000",
    "경기도": "6410000",
    "강원특별자치도": "6420000",
    "충청북도": "6440000",
    "충청남도": "6450000",
    "전북특별자치도": "6460000",
    "전라남도": "6470000",
    "경상북도": "6480000",
    "경상남도": "6490000",
    "제주특별자치도": "6500000",
}
