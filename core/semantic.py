"""Semantic Scholar API client. No API key required (optional for higher rate limits)."""

import httpx

BASE_URL = "https://api.semanticscholar.org/graph/v1"


def _extract_authors(authors: list[dict] | None) -> list[str]:
    """Extract author name strings from Semantic Scholar author dicts."""
    if not authors:
        return []
    return [a.get("name", "") for a in authors if a.get("name")]


def _extract_doi(external_ids: dict | None) -> str | None:
    """Extract DOI from externalIds dict."""
    if not external_ids:
        return None
    return external_ids.get("DOI")


def search_papers(
    query: str,
    limit: int = 5,
    fields: str = "title,authors,year,citationCount,abstract,externalIds,url",
) -> list[dict]:
    """Search for papers on Semantic Scholar.

    Args:
        query: Search query string.
        limit: Maximum number of results.
        fields: Comma-separated list of fields to return.

    Returns:
        List of paper dicts.
    """
    params = {"query": query, "limit": limit, "fields": fields}

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{BASE_URL}/paper/search", params=params)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Semantic Scholar search failed: {exc}") from exc

    data = resp.json()
    papers = data.get("data", [])

    results: list[dict] = []
    for p in papers:
        results.append({
            "paperId": p.get("paperId"),
            "title": p.get("title"),
            "authors": _extract_authors(p.get("authors")),
            "year": p.get("year"),
            "citationCount": p.get("citationCount"),
            "abstract": p.get("abstract"),
            "doi": _extract_doi(p.get("externalIds")),
            "url": p.get("url"),
        })

    return results


def get_paper(
    paper_id: str,
    fields: str = "title,authors,year,citationCount,influentialCitationCount,abstract,references,citations,externalIds,url",
) -> dict:
    """Get detailed information about a single paper.

    Args:
        paper_id: Semantic Scholar paper ID, DOI, or arXiv ID (e.g. "arXiv:2603.12345").
        fields: Comma-separated list of fields to return.

    Returns:
        Paper dict with all requested fields.
    """
    params = {"fields": fields}

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{BASE_URL}/paper/{paper_id}", params=params)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Semantic Scholar get_paper failed for {paper_id}: {exc}") from exc

    p = resp.json()

    # Process authors and DOI at top level
    if "authors" in p:
        p["authors"] = _extract_authors(p["authors"])
    if "externalIds" in p:
        p["doi"] = _extract_doi(p["externalIds"])

    # Process nested references and citations author lists
    for ref in p.get("references", []) or []:
        if isinstance(ref, dict) and "citingPaper" not in ref and "citedPaper" not in ref:
            if "authors" in ref:
                ref["authors"] = _extract_authors(ref["authors"])
        elif isinstance(ref, dict):
            inner = ref.get("citedPaper", ref)
            if "authors" in inner:
                inner["authors"] = _extract_authors(inner["authors"])

    for cit in p.get("citations", []) or []:
        if isinstance(cit, dict) and "citingPaper" in cit:
            inner = cit["citingPaper"]
            if "authors" in inner:
                inner["authors"] = _extract_authors(inner["authors"])
        elif isinstance(cit, dict) and "authors" in cit:
            cit["authors"] = _extract_authors(cit["authors"])

    return p


def get_citations(
    paper_id: str,
    limit: int = 5,
    fields: str = "title,authors,year,citationCount",
) -> list[dict]:
    """Get papers that cite the given paper.

    Args:
        paper_id: Semantic Scholar paper ID.
        limit: Maximum number of citations to return.
        fields: Comma-separated list of fields for each citing paper.

    Returns:
        List of citing paper dicts.
    """
    params = {"limit": limit, "fields": fields}

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{BASE_URL}/paper/{paper_id}/citations", params=params)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Semantic Scholar get_citations failed for {paper_id}: {exc}") from exc

    data = resp.json()
    results: list[dict] = []
    for item in data.get("data", []):
        citing = item.get("citingPaper", item)
        if "authors" in citing:
            citing["authors"] = _extract_authors(citing["authors"])
        results.append(citing)

    return results


def get_references(
    paper_id: str,
    limit: int = 5,
    fields: str = "title,authors,year,citationCount",
) -> list[dict]:
    """Get papers referenced by the given paper.

    Args:
        paper_id: Semantic Scholar paper ID.
        limit: Maximum number of references to return.
        fields: Comma-separated list of fields for each referenced paper.

    Returns:
        List of referenced paper dicts.
    """
    params = {"limit": limit, "fields": fields}

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{BASE_URL}/paper/{paper_id}/references", params=params)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Semantic Scholar get_references failed for {paper_id}: {exc}") from exc

    data = resp.json()
    results: list[dict] = []
    for item in data.get("data", []):
        cited = item.get("citedPaper", item)
        if "authors" in cited:
            cited["authors"] = _extract_authors(cited["authors"])
        results.append(cited)

    return results


def find_related(
    paper_id: str,
    limit: int = 5,
    fields: str = "title,authors,year,citationCount,abstract",
) -> list[dict]:
    """Find papers related/recommended based on a given paper.

    Args:
        paper_id: Semantic Scholar paper ID.
        limit: Maximum number of recommendations.
        fields: Comma-separated list of fields for each recommended paper.

    Returns:
        List of recommended paper dicts.
    """
    params = {"limit": limit, "fields": fields}

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"https://api.semanticscholar.org/recommendations/v1/papers/forpaper/{paper_id}",
                params=params,
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Semantic Scholar find_related failed for {paper_id}: {exc}") from exc

    data = resp.json()
    results: list[dict] = []
    for p in data.get("recommendedPapers", []):
        if "authors" in p:
            p["authors"] = _extract_authors(p["authors"])
        results.append(p)

    return results
