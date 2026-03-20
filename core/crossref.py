"""CrossRef API client. No API key required."""

import httpx

BASE_URL = "https://api.crossref.org"

HEADERS = {
    "User-Agent": "academic-research-mcp/0.1.0 (https://github.com/wjddusrb03/academic-research-mcp)",
}


def _parse_authors(author_list: list[dict] | None) -> list[str]:
    """Convert CrossRef author dicts to 'given family' strings."""
    if not author_list:
        return []
    results = []
    for a in author_list:
        given = a.get("given", "")
        family = a.get("family", "")
        name = f"{given} {family}".strip()
        if name:
            results.append(name)
    return results


def _parse_date(date_parts: dict | None) -> str:
    """Extract a date string from CrossRef date-parts structure."""
    if not date_parts:
        return ""
    parts = date_parts.get("date-parts", [[]])
    if not parts or not parts[0]:
        return ""
    components = parts[0]
    # components is [year] or [year, month] or [year, month, day]
    return "-".join(str(c).zfill(2) if i > 0 else str(c) for i, c in enumerate(components))


def get_bibtex(doi: str) -> str:
    """Fetch BibTeX citation for a given DOI.

    Args:
        doi: Digital Object Identifier.

    Returns:
        BibTeX string.
    """
    url = f"{BASE_URL}/works/{doi}/transform/application/x-bibtex"
    headers = {**HEADERS, "Accept": "application/x-bibtex"}

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"CrossRef BibTeX request failed for DOI {doi}: {exc}") from exc

    return resp.text


def get_metadata(doi: str) -> dict:
    """Fetch metadata for a given DOI.

    Args:
        doi: Digital Object Identifier.

    Returns:
        Dict with title, authors, published_date, journal, doi, type.
    """
    url = f"{BASE_URL}/works/{doi}"

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=HEADERS)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"CrossRef metadata request failed for DOI {doi}: {exc}") from exc

    data = resp.json()
    msg = data.get("message", {})

    title_list = msg.get("title", [])
    title = title_list[0] if title_list else ""

    return {
        "title": title,
        "authors": _parse_authors(msg.get("author")),
        "published_date": _parse_date(msg.get("published") or msg.get("issued")),
        "journal": (msg.get("container-title") or [""])[0] if msg.get("container-title") else "",
        "doi": msg.get("DOI", ""),
        "type": msg.get("type", ""),
    }


def search_works(query: str, rows: int = 5) -> list[dict]:
    """Search CrossRef works by query string.

    Args:
        query: Search query.
        rows: Maximum number of results.

    Returns:
        List of work dicts.
    """
    params = {"query": query, "rows": rows}

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{BASE_URL}/works", params=params, headers=HEADERS)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"CrossRef search failed: {exc}") from exc

    data = resp.json()
    items = data.get("message", {}).get("items", [])

    results: list[dict] = []
    for item in items:
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""

        container = item.get("container-title", [])
        journal = container[0] if container else ""

        results.append({
            "title": title,
            "authors": _parse_authors(item.get("author")),
            "published_date": _parse_date(item.get("published") or item.get("issued")),
            "doi": item.get("DOI", ""),
            "journal": journal,
            "citation_count": item.get("is-referenced-by-count", 0),
        })

    return results
