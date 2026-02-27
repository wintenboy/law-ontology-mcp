"""Ontology network visualization — builds graph data and generates HTML."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import webbrowser
from pathlib import Path

from .sparql_client import LawOntologyClient
from .queries import (
    get_ontology_classes_query,
    get_ontology_object_properties_query,
    get_ontology_data_properties_query,
    get_subclass_relations_query,
    list_laws_query,
)
from .prefixes import LAW_TYPE_MAP

logger = logging.getLogger("law-ontology-mcp")

TEMPLATE_PATH = Path(__file__).parent / "templates" / "network.html"

CLASS_COLORS = {
    "KoreanLegislation": ("#3b82f6", "#2563eb"),
    "KoreanPrecedent": ("#10b981", "#059669"),
    "KoreanPrecedentCase": ("#10b981", "#059669"),
    "KoreanOrdinance": ("#f59e0b", "#d97706"),
    "KoreanAdministrativeRules": ("#ef4444", "#dc2626"),
    "KoreanTreaty": ("#8b5cf6", "#7c3aed"),
    "KoreanConstitutionalCourtCase": ("#ec4899", "#db2777"),
    "KoreanAdministrativeTrialCase": ("#f97316", "#ea580c"),
    "KoreanCommitteeDicision": ("#06b6d4", "#0891b2"),
    "KoreanExplanationCase": ("#84cc16", "#65a30d"),
    "KoreanSchoolPublicRules": ("#a855f7", "#9333ea"),
    "KoreanLegislationNorms": ("#6366f1", "#4f46e5"),
}


def _color_for_class(class_uri: str) -> tuple[str, str]:
    for key, colors in CLASS_COLORS.items():
        if key in class_uri:
            return colors
    return ("#64748b", "#475569")


def _shorten_uri(uri: str) -> str:
    if "Class/" in uri:
        return uri.split("Class/")[-1]
    if "property/" in uri:
        return uri.split("property/")[-1]
    if "resource/" in uri:
        return uri.split("resource/")[-1]
    if "#" in uri:
        return uri.split("#")[-1]
    if "/" in uri:
        return uri.split("/")[-1]
    return uri


async def build_ontology_graph(client: LawOntologyClient) -> dict:
    """Fetch ontology metadata and build graph data for vis.js."""
    nodes = []
    edges = []
    node_ids = set()

    # 1. Fetch classes — aggregate multiple labels per class URI
    classes = await client.sparql(get_ontology_classes_query())

    # Group labels by class URI
    class_labels: dict[str, list[str]] = {}
    for row in classes:
        class_uri = row.get("class", "")
        label = row.get("label", "")
        if not class_uri:
            continue
        # Skip non-LOD classes (owl, rdf, rdfs, skos)
        if "lod.law.go.kr" not in class_uri:
            continue
        if class_uri not in class_labels:
            class_labels[class_uri] = []
        if label:
            class_labels[class_uri].append(label)

    for class_uri, labels in class_labels.items():
        short = _shorten_uri(class_uri)

        # Pick best Korean label (contains Hangul) or English label
        korean_label = ""
        english_label = ""
        for lbl in labels:
            if any("\uac00" <= ch <= "\ud7a3" for ch in lbl):
                korean_label = lbl
            else:
                english_label = lbl

        display_label = korean_label or english_label or short
        display = f"{short}\n({display_label})" if display_label != short else short

        bg, border = _color_for_class(class_uri)
        node_id = class_uri

        if node_id not in node_ids:
            node_ids.add(node_id)
            nodes.append({
                "id": node_id,
                "label": display,
                "uri": class_uri,
                "koreanLabel": korean_label,
                "englishLabel": english_label,
                "nodeType": "클래스",
                "color": bg,
                "borderColor": border,
                "size": 28,
                "fontSize": 14,
                "shape": "dot",
                "properties": [],
                "samples": [],
            })

    # 2. Fetch object properties (edges between classes)
    obj_props = await client.sparql(get_ontology_object_properties_query())

    # Deduplicate: group by (prop, domain, range), pick best label
    seen_obj_edges: set[str] = set()
    for row in obj_props:
        prop_uri = row.get("prop", "")
        label = row.get("label", "")
        domain = row.get("domain", "")
        range_ = row.get("range", "")

        if not prop_uri:
            continue

        short = _shorten_uri(prop_uri)
        # Prefer Korean label
        edge_label = label if label else short
        edge_key = f"{prop_uri}|{domain}|{range_}"
        if edge_key in seen_obj_edges:
            continue
        seen_obj_edges.add(edge_key)

        if domain and range_ and domain in node_ids and range_ in node_ids:
            edges.append({
                "from": domain,
                "to": range_,
                "label": short,
                "title": f"{edge_label}: {_shorten_uri(domain)} \u2192 {_shorten_uri(range_)}",
            })
        elif domain and domain in node_ids:
            for n in nodes:
                if n["id"] == domain:
                    prop_display = f"\u2192 {edge_label}" if edge_label != short else f"\u2192 {short}"
                    if prop_display not in n["properties"]:
                        n["properties"].append(prop_display)
                    break

    # 3. Fetch data properties (listed on class nodes)
    data_props = await client.sparql(get_ontology_data_properties_query())

    seen_data_props: set[str] = set()
    for row in data_props:
        prop_uri = row.get("prop", "")
        label = row.get("label", "")
        domain = row.get("domain", "")

        if not prop_uri or not domain:
            continue

        dp_key = f"{prop_uri}|{domain}"
        if dp_key in seen_data_props:
            continue
        seen_data_props.add(dp_key)

        short = _shorten_uri(prop_uri)
        prop_label = label if label else short

        for n in nodes:
            if n["id"] == domain:
                if prop_label not in n["properties"]:
                    n["properties"].append(prop_label)
                break

    # 4. Fetch subclass relations
    subclasses = await client.sparql(get_subclass_relations_query())

    for row in subclasses:
        sub = row.get("sub", "")
        super_ = row.get("super", "")
        if sub in node_ids and super_ in node_ids:
            edges.append({
                "from": sub,
                "to": super_,
                "label": "subClassOf",
                "dashes": True,
                "title": f"{_shorten_uri(sub)} \u2282 {_shorten_uri(super_)}",
            })

    # 5. Fetch sample laws for major classes
    for type_name, class_const in list(LAW_TYPE_MAP.items())[:6]:
        class_uri = f"http://lod.law.go.kr/Class/{class_const.replace('ldc:', '')}"
        if class_uri not in node_ids:
            continue
        try:
            query = list_laws_query(type_name, limit=3)
            samples = await client.sparql(query)
            for n in nodes:
                if n["id"] == class_uri:
                    n["samples"] = [
                        {"label": s.get("lawName", ""), "uri": s.get("law", "")}
                        for s in samples
                    ]
                    break
        except Exception:
            pass

    return {"nodes": nodes, "edges": edges}


async def build_law_network_graph(
    client: LawOntologyClient, keyword: str, limit: int = 10
) -> dict:
    """Search laws by keyword and build a relationship network graph."""
    nodes = []
    edges = []
    node_ids: set[str] = set()

    search_results = await client.search(keyword, limit=limit)
    if not search_results:
        return {"nodes": [], "edges": []}

    for result in search_results:
        uri = result.get("uri", "")
        label = result.get("label", "")
        law_type = result.get("type", "")
        resource_id = uri.split("/")[-1] if "/" in uri else uri

        if not resource_id or resource_id in node_ids:
            continue

        try:
            detail = await client.get_detail_with_links(resource_id)
        except Exception:
            detail = []

        detail_dict: dict[str, list[str]] = {}
        linked_resources: list[dict] = []

        for prop in detail:
            prop_name = prop.get("property", "")
            value = prop.get("value", "")
            link_uri = prop.get("link_uri", "")

            if prop_name not in detail_dict:
                detail_dict[prop_name] = []
            detail_dict[prop_name].append(value)

            if link_uri:
                linked_resources.append({
                    "property": prop_name,
                    "value": value,
                    "uri": link_uri,
                })

        # Keep key properties for display
        filtered_detail: dict[str, list[str]] = {}
        for k, v in detail_dict.items():
            filtered_detail[k] = v[:3]

        bg, border = _color_for_class(law_type)
        node_ids.add(resource_id)
        nodes.append({
            "id": resource_id,
            "label": label[:30] if label else resource_id,
            "title": label,
            "uri": uri,
            "resourceId": resource_id,
            "lawType": law_type,
            "color": bg,
            "borderColor": border,
            "size": 22,
            "detail": filtered_detail,
        })

        for linked in linked_resources:
            linked_id = linked["uri"].split("/")[-1]
            edge_label = linked["property"].split("(")[0].strip()

            if linked_id not in node_ids:
                node_ids.add(linked_id)
                nodes.append({
                    "id": linked_id,
                    "label": linked["value"][:30],
                    "title": linked["value"],
                    "uri": linked["uri"],
                    "resourceId": linked_id,
                    "lawType": "",
                    "color": "#475569",
                    "borderColor": "#334155",
                    "size": 14,
                    "detail": {},
                })

            edges.append({
                "from": resource_id,
                "to": linked_id,
                "label": edge_label,
                "title": f"{label} \u2192 {linked['value']} ({edge_label})",
            })

    return {"nodes": nodes, "edges": edges}


def generate_html(
    ontology_data: dict,
    law_network_data: dict | None = None,
    output_path: str | None = None,
) -> str:
    """Generate the visualization HTML file from graph data."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    has_law = (
        law_network_data is not None
        and len(law_network_data.get("nodes", [])) > 0
    )

    html = template.replace(
        "{{ONTOLOGY_DATA}}", json.dumps(ontology_data, ensure_ascii=False)
    )
    html = html.replace(
        "{{LAW_NETWORK_DATA}}",
        json.dumps(law_network_data or {"nodes": [], "edges": []}, ensure_ascii=False),
    )
    html = html.replace("{{HAS_LAW_NETWORK}}", "true" if has_law else "false")
    html = html.replace("{{LAW_TAB_CLASS}}", "" if has_law else "disabled")

    if output_path:
        path = Path(output_path)
    else:
        fd, tmp = tempfile.mkstemp(suffix=".html", prefix="law-ontology-")
        os.close(fd)
        path = Path(tmp)

    path.write_text(html, encoding="utf-8")
    return str(path)


def open_in_browser(file_path: str) -> None:
    """Open the generated HTML file in the default browser."""
    webbrowser.open(f"file:///{file_path.replace(os.sep, '/')}")
