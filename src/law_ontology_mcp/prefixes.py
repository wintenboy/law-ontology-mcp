"""SPARQL PREFIX definitions for Korean law ontology."""

PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "ldc": "http://lod.law.go.kr/Class/",
    "ldp": "http://lod.law.go.kr/property/",
    "ldr": "http://lod.law.go.kr/resource/",
}

DEFAULT_PREFIX_BLOCK = "\n".join(
    f"PREFIX {k}: <{v}>" for k, v in PREFIXES.items()
)

# Class URIs
CLASS_LEGISLATION = "ldc:KoreanLegislation"
CLASS_ADMIN_RULES = "ldc:KoreanAdministrativeRules"
CLASS_ORDINANCE = "ldc:KoreanOrdinance"
CLASS_PRECEDENT = "ldc:KoreanPrecedent"
CLASS_PRECEDENT_CASE = "ldc:KoreanPrecedentCase"
CLASS_CONSTITUTIONAL = "ldc:KoreanConstitutionalCourtCase"
CLASS_ADMIN_TRIAL = "ldc:KoreanAdministrativeTrialCase"
CLASS_COMMITTEE = "ldc:KoreanCommitteeDicision"
CLASS_EXPLANATION = "ldc:KoreanExplanationCase"
CLASS_SCHOOL_RULES = "ldc:KoreanSchoolPublicRules"
CLASS_TREATY = "ldc:KoreanTreaty"
CLASS_NORMS = "ldc:KoreanLegislationNorms"

LAW_TYPE_MAP = {
    "법령": CLASS_LEGISLATION,
    "현행법령": CLASS_LEGISLATION,
    "행정규칙": CLASS_ADMIN_RULES,
    "자치법규": CLASS_ORDINANCE,
    "판례": CLASS_PRECEDENT,
    "헌법재판소": CLASS_CONSTITUTIONAL,
    "행정심판": CLASS_ADMIN_TRIAL,
    "위원회결정": CLASS_COMMITTEE,
    "유권해석": CLASS_EXPLANATION,
    "학칙": CLASS_SCHOOL_RULES,
    "조약": CLASS_TREATY,
}
