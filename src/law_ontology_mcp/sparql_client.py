"""SPARQL HTTP client with HTML response parsing and caching."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup
from cachetools import TTLCache

logger = logging.getLogger("law-ontology-mcp")

SPARQL_ENDPOINT = "https://lod.law.go.kr/DRF/lod/sparql.do"
SEARCH_ENDPOINT = "https://lod.law.go.kr/DRF/lod/getSearch.do"
DETAIL_ENDPOINT = "https://lod.law.go.kr/DRF/lod/page"
CACHE_TTL = 3600  # 1 hour
CACHE_MAX = 500
REQUEST_TIMEOUT = 60.0
MAX_RETRIES = 3
RETRY_DELAYS = [1.0, 2.0, 4.0]  # Exponential backoff


class LawOntologyClient:
    """Client for Korean law ontology platform with SPARQL + search + detail APIs."""

    def __init__(self) -> None:
        self._cache: TTLCache = TTLCache(maxsize=CACHE_MAX, ttl=CACHE_TTL)
        self._client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": "law-ontology-mcp/1.0",
                "Accept-Charset": "UTF-8",
            },
            follow_redirects=True,
        )

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Execute HTTP request with automatic retry on timeout."""
        last_exc = None
        for attempt in range(MAX_RETRIES):
            try:
                if method == "GET":
                    return await self._client.get(url, **kwargs)
                else:
                    return await self._client.post(url, **kwargs)
            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout) as e:
                last_exc = e
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(f"Timeout (attempt {attempt + 1}/{MAX_RETRIES}), retrying in {delay}s...")
                    await asyncio.sleep(delay)
        raise last_exc

    async def close(self) -> None:
        await self._client.aclose()

    def _cache_key(self, prefix: str, query: str) -> str:
        return hashlib.md5(f"{prefix}:{query}".encode()).hexdigest()

    # ── SPARQL API ──────────────────────────────────────────────

    async def sparql(self, query: str) -> list[dict[str, str]]:
        """Execute a SPARQL query via POST and return parsed results.

        Note: The LOD endpoint does NOT support string functions in FILTER
        (contains, str, regex, lang). Only URI comparisons work in FILTER.
        """
        key = self._cache_key("sparql", query)
        if key in self._cache:
            return self._cache[key]

        # Build form-encoded body (server requires this exact format)
        body = f"query={quote(query, safe='')}&timeout=60"

        response = await self._request_with_retry(
            "POST",
            SPARQL_ENDPOINT,
            content=body.encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )
        response.raise_for_status()

        results = self._parse_sparql_table(response.text)
        self._cache[key] = results
        return results

    def _parse_sparql_table(self, html: str) -> list[dict[str, str]]:
        """Parse the HTML table from SPARQL endpoint response."""
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", id="tb_result")
        if not table:
            return []

        headers: list[str] = []
        thead = table.find("thead")
        if thead:
            for th in thead.find_all("th"):
                headers.append(th.get_text(strip=True))
        if not headers:
            return []

        rows: list[dict[str, str]] = []
        tbody = table.find("tbody")
        if not tbody:
            return []

        for tr in tbody.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) != len(headers):
                continue

            row: dict[str, str] = {}
            for i, td in enumerate(cells):
                a_tag = td.find("a")
                value = a_tag.get_text(strip=True) if a_tag else td.get_text(strip=True)
                # Clean language tags: "value"@ko → value
                value = re.sub(r'^"(.*)"@\w+$', r"\1", value)
                # Clean datatype: "value"^^xsd:string → value
                value = re.sub(r'^"(.*)"\^\^.*$', r"\1", value)
                # Clean HTML entities
                value = value.replace("&#034;", '"').replace("&amp;", "&")
                row[headers[i]] = value
            rows.append(row)

        return rows

    # ── Search API ──────────────────────────────────────────────

    async def search(
        self,
        keyword: str,
        law_type: str = "",
        agency: str = "",
        limit: int = 10,
        order: str = "ASC(?label)",
    ) -> list[dict[str, str]]:
        """Search laws via the getSearch.do endpoint (supports Korean text search)."""
        key = self._cache_key("search", f"{keyword}:{law_type}:{agency}:{limit}:{order}")
        if key in self._cache:
            return self._cache[key]

        params = {
            "keyword": keyword,
            "type": law_type,
            "agency": agency,
            "limit": str(limit),
            "order": order,
        }

        response = await self._request_with_retry("GET", SEARCH_ENDPOINT, params=params)
        response.raise_for_status()

        results = self._parse_search_results(response.text)
        self._cache[key] = results
        return results

    def _parse_search_results(self, html: str) -> list[dict[str, str]]:
        """Parse search results from getSearch.do HTML response."""
        soup = BeautifulSoup(html, "lxml")
        results: list[dict[str, str]] = []

        result_zone = soup.find("div", id="resultZone")
        if not result_zone:
            # Fallback: look for all div.list elements
            result_zone = soup

        for item in result_zone.find_all("div", class_="list"):
            row: dict[str, str] = {}

            dl = item.find("dl")
            if not dl:
                continue

            # Extract label (Resources dd)
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")

            for dt, dd in zip(dts, dds):
                dt_text = dt.get_text(strip=True)

                if dt_text == "Resources":
                    # Label is the text before <br>, URI is in the <a> tag
                    label_text = ""
                    for child in dd.children:
                        if child.name == "br":
                            break
                        if child.name == "a":
                            continue
                        text = child.get_text(strip=True) if hasattr(child, "get_text") else str(child).strip()
                        if text:
                            label_text += text

                    # Clean language tag
                    label_text = re.sub(r"@\w+$", "", label_text).strip()

                    a_tag = dd.find("a")
                    uri = a_tag.get("href", "") if a_tag else ""
                    # Convert relative paths to resource URIs
                    if uri.startswith("/DRF/lod/page/"):
                        resource_id = uri.replace("/DRF/lod/page/", "").replace(".do", "")
                        uri = f"http://lod.law.go.kr/resource/{resource_id}"

                    row["label"] = label_text
                    row["uri"] = uri

                elif dt_text == "Description":
                    desc = dd.get_text(strip=True)
                    # Clean up
                    desc = re.sub(r'^"', "", desc)
                    desc = desc.replace("━", "").replace("┯", "").replace("├", "").replace("─", "")
                    if len(desc) > 300:
                        desc = desc[:300] + "..."
                    row["description"] = desc

            # Extract class URI from hidden input
            class_input = item.find("input", {"name": "classUri"})
            if class_input:
                class_uri = class_input.get("value", "")
                # Simplify class name
                row["type"] = class_uri.replace("http://lod.law.go.kr/Class/", "")

            if row.get("label"):
                results.append(row)

        return results

    # ── Detail API ──────────────────────────────────────────────

    async def get_detail(self, resource_id: str) -> list[dict[str, str]]:
        """Get detail info for a resource via page endpoint."""
        key = self._cache_key("detail", resource_id)
        if key in self._cache:
            return self._cache[key]

        url = f"{DETAIL_ENDPOINT}/{resource_id}.do"
        response = await self._request_with_retry("GET", url)
        response.raise_for_status()

        results = self._parse_detail_page(response.text)
        self._cache[key] = results
        return results

    def _parse_detail_page(self, html: str) -> list[dict[str, str]]:
        """Parse property-value pairs from resource detail page."""
        soup = BeautifulSoup(html, "lxml")
        results: list[dict[str, str]] = []

        table = soup.find("table")
        if not table:
            return []

        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue

            prop_cell = cells[0]
            val_cell = cells[1]

            # Extract property: "ldp:lawName (법령명@ko)" → "lawName (법령명)"
            prop_link = prop_cell.find("a")
            prop_raw = prop_link.get_text(strip=True) if prop_link else prop_cell.get_text(strip=True)
            # Clean: "ldp:propName (설명@ko)" → "propName (설명)"
            prop = prop_raw.replace("ldp:", "").replace("rdfs:", "rdfs:")
            prop = re.sub(r"@\w+", "", prop).strip()

            # Extract value: get text, remove type annotations
            # Remove all <a> tags that are type references (xsd:string etc)
            for a in val_cell.find_all("a"):
                href = a.get("href", "")
                if "XMLSchema" in href or "rdf-syntax" in href:
                    a.decompose()

            # Check for resource links (ldr: references with labels)
            resource_links = val_cell.find_all("a")
            if resource_links:
                # Find the most descriptive link (last one usually has label)
                best_text = ""
                for link in resource_links:
                    text = link.get_text(strip=True)
                    if text and len(text) > len(best_text):
                        best_text = text
                if best_text:
                    val = best_text
                else:
                    val = val_cell.get_text(strip=True)
            else:
                val = val_cell.get_text(strip=True)

            # Clean up value
            val = re.sub(r"@\w+\(?[^)]*\)?", "", val).strip()  # Remove @ko(xsd:string)
            val = re.sub(r"\s+", " ", val).strip()  # Collapse whitespace
            val = val.strip('"').strip()

            if prop and val and val not in ("()", ""):
                results.append({"property": prop, "value": val})

        return results

    async def get_detail_with_links(self, resource_id: str) -> list[dict[str, str]]:
        """Get detail info with resource link URIs preserved."""
        key = self._cache_key("detail_links", resource_id)
        if key in self._cache:
            return self._cache[key]

        url = f"{DETAIL_ENDPOINT}/{resource_id}.do"
        response = await self._request_with_retry("GET", url)
        response.raise_for_status()

        results = self._parse_detail_page_with_links(response.text)
        self._cache[key] = results
        return results

    def _parse_detail_page_with_links(self, html: str) -> list[dict[str, str]]:
        """Parse detail page, preserving resource link URIs for graph building."""
        soup = BeautifulSoup(html, "lxml")
        results: list[dict[str, str]] = []

        table = soup.find("table")
        if not table:
            return []

        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue

            prop_cell = cells[0]
            val_cell = cells[1]

            prop_link = prop_cell.find("a")
            prop_raw = prop_link.get_text(strip=True) if prop_link else prop_cell.get_text(strip=True)
            prop = prop_raw.replace("ldp:", "").replace("rdfs:", "rdfs:")
            prop = re.sub(r"@\w+", "", prop).strip()

            for a in val_cell.find_all("a"):
                href = a.get("href", "")
                if "XMLSchema" in href or "rdf-syntax" in href:
                    a.decompose()

            resource_links = val_cell.find_all("a")
            link_uri = ""
            if resource_links:
                best_text = ""
                for link in resource_links:
                    text = link.get_text(strip=True)
                    href = link.get("href", "")
                    if text and len(text) > len(best_text):
                        best_text = text
                        if href.startswith("/DRF/lod/page/"):
                            rid = href.replace("/DRF/lod/page/", "").replace(".do", "")
                            link_uri = f"http://lod.law.go.kr/resource/{rid}"
                        elif href.startswith("http://lod.law.go.kr/"):
                            link_uri = href
                val = best_text if best_text else val_cell.get_text(strip=True)
            else:
                val = val_cell.get_text(strip=True)

            val = re.sub(r"@\w+\(?[^)]*\)?", "", val).strip()
            val = re.sub(r"\s+", " ", val).strip()
            val = val.strip('"').strip()

            if prop and val and val not in ("()", ""):
                row = {"property": prop, "value": val}
                if link_uri:
                    row["link_uri"] = link_uri
                results.append(row)

        return results

    def clear_cache(self) -> int:
        """Clear all cached results. Returns count of cleared entries."""
        count = len(self._cache)
        self._cache.clear()
        return count
