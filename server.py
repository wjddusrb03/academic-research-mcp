"""
academic-research-mcp — MCP server for academic research
Search papers, analyze citations, generate BibTeX, translate abstracts.
Most features work without any API key.
"""

import argparse
import sys
import datetime

from mcp.server.fastmcp import FastMCP

import core.arxiv as arxiv
import core.semantic as semantic
import core.crossref as crossref
import core.translator as translator

mcp = FastMCP("academic-research")


# ──────────────────────────────────────────────
# API Status
# ──────────────────────────────────────────────

@mcp.tool()
def api_status() -> str:
    """Check which APIs are available."""
    papago_ok = translator.is_available()

    lines = ["## API Status\n"]
    lines.append("  arXiv:            [OK] Ready (no key needed)")
    lines.append("  Semantic Scholar: [OK] Ready (no key needed)")
    lines.append("  CrossRef:         [OK] Ready (no key needed)")
    lines.append(f"  Papago (translate): {'[OK] Ready' if papago_ok else '[--] Not configured (optional, https://developers.naver.com)'}")
    lines.append("")

    if papago_ok:
        lines.append("All features available.")
    else:
        lines.append("Translation is disabled. All other features work normally.")
        lines.append("To enable: add NAVER_CLIENT_ID + NAVER_CLIENT_SECRET to .env")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# Paper Search
# ──────────────────────────────────────────────

@mcp.tool()
def search_papers(query: str, count: int = 5, source: str = "both") -> str:
    """Search for academic papers by keyword.

    - query: Search keywords (e.g. 'transformer attention mechanism')
    - count: Number of results (default: 5)
    - source: 'arxiv', 'semantic', or 'both' (default)
    """
    sections = [f"## Paper Search: '{query}'\n"]

    if source in ("arxiv", "both"):
        sections.append("### arXiv Results\n")
        try:
            papers = arxiv.search_papers(query, max_results=count)
            if papers:
                for i, p in enumerate(papers, 1):
                    authors = ", ".join(p["authors"][:3])
                    if len(p["authors"]) > 3:
                        authors += " et al."
                    sections.append(f"  {i}. **{p['title']}**")
                    sections.append(f"     Authors: {authors}")
                    sections.append(f"     Date: {p['published'][:10]} | Category: {p['categories']}")
                    sections.append(f"     PDF: {p['pdf_url']}")
                    sections.append(f"     ID: {p['id']}")
                    sections.append("")
            else:
                sections.append("  No results found.\n")
        except Exception as e:
            sections.append(f"  [Error] arXiv search failed: {e}\n")

    if source in ("semantic", "both"):
        sections.append("### Semantic Scholar Results\n")
        try:
            papers = semantic.search_papers(query, limit=count)
            if papers:
                for i, p in enumerate(papers, 1):
                    authors = ", ".join(p["authors"][:3])
                    if len(p["authors"]) > 3:
                        authors += " et al."
                    sections.append(f"  {i}. **{p['title']}**")
                    sections.append(f"     Authors: {authors}")
                    sections.append(f"     Year: {p.get('year', 'N/A')} | Citations: {p.get('citationCount', 0)}")
                    if p.get("doi"):
                        sections.append(f"     DOI: {p['doi']}")
                    sections.append(f"     URL: {p.get('url', '')}")
                    sections.append("")
            else:
                sections.append("  No results found.\n")
        except Exception as e:
            sections.append(f"  [Error] Semantic Scholar search failed: {e}\n")

    return "\n".join(sections)


# ──────────────────────────────────────────────
# Paper Detail
# ──────────────────────────────────────────────

@mcp.tool()
def paper_detail(paper_id: str) -> str:
    """Get detailed info about a paper including citations and references.

    - paper_id: Semantic Scholar ID, DOI (e.g. '10.xxxx/...'), or arXiv ID (e.g. 'arXiv:2603.12345')
    """
    sections = []

    try:
        p = semantic.get_paper(paper_id)
    except Exception as e:
        return f"[Error] Could not fetch paper: {e}"

    sections.append(f"## {p.get('title', 'Unknown')}\n")

    authors = p.get("authors", [])
    if isinstance(authors, list) and authors:
        if isinstance(authors[0], str):
            sections.append(f"**Authors:** {', '.join(authors)}")
        else:
            sections.append(f"**Authors:** {authors}")

    sections.append(f"**Year:** {p.get('year', 'N/A')}")
    sections.append(f"**Citations:** {p.get('citationCount', 0)} (Influential: {p.get('influentialCitationCount', 0)})")

    doi = p.get("doi")
    if doi:
        sections.append(f"**DOI:** {doi}")
    sections.append(f"**URL:** {p.get('url', '')}")
    sections.append("")

    abstract = p.get("abstract", "")
    if abstract:
        sections.append(f"### Abstract\n\n{abstract}\n")

    # Top citations
    citations = p.get("citations", [])
    if citations:
        sections.append("### Top Citing Papers\n")
        for i, c in enumerate(citations[:5], 1):
            inner = c.get("citingPaper", c) if isinstance(c, dict) else c
            if isinstance(inner, dict):
                sections.append(f"  {i}. {inner.get('title', 'N/A')}")
        sections.append("")

    # Top references
    refs = p.get("references", [])
    if refs:
        sections.append("### Key References\n")
        for i, r in enumerate(refs[:5], 1):
            inner = r.get("citedPaper", r) if isinstance(r, dict) else r
            if isinstance(inner, dict):
                sections.append(f"  {i}. {inner.get('title', 'N/A')}")
        sections.append("")

    return "\n".join(sections)


# ──────────────────────────────────────────────
# Related Papers
# ──────────────────────────────────────────────

@mcp.tool()
def find_related(paper_id: str, count: int = 5) -> str:
    """Find papers related to a given paper.

    - paper_id: Semantic Scholar paper ID
    - count: Number of recommendations (default: 5)
    """
    try:
        papers = semantic.find_related(paper_id, limit=count)
    except Exception as e:
        return f"[Error] Could not find related papers: {e}"

    if not papers:
        return "No related papers found."

    lines = ["## Related Papers\n"]
    for i, p in enumerate(papers, 1):
        authors = p.get("authors", [])
        if isinstance(authors, list) and authors and isinstance(authors[0], str):
            author_str = ", ".join(authors[:3])
        else:
            author_str = "N/A"
        lines.append(f"### {i}. {p.get('title', 'N/A')}")
        lines.append(f"  Authors: {author_str}")
        lines.append(f"  Year: {p.get('year', 'N/A')} | Citations: {p.get('citationCount', 0)}")
        abstract = p.get("abstract", "")
        if abstract:
            lines.append(f"  Abstract: {abstract[:200]}...")
        lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# BibTeX
# ──────────────────────────────────────────────

@mcp.tool()
def get_bibtex(doi: str) -> str:
    """Generate BibTeX citation from a DOI.

    - doi: Digital Object Identifier (e.g. '10.1038/nature12373')
    """
    try:
        bibtex = crossref.get_bibtex(doi)
    except Exception as e:
        return f"[Error] BibTeX generation failed: {e}"

    return f"## BibTeX Citation\n\n```bibtex\n{bibtex}\n```"


# ──────────────────────────────────────────────
# Translation
# ──────────────────────────────────────────────

@mcp.tool()
def translate_abstract(text: str, source: str = "en", target: str = "ko") -> str:
    """Translate academic text (abstract, title, etc.) using Papago.
    Requires Naver API key in .env (optional feature).

    - text: Text to translate
    - source: Source language (default: en)
    - target: Target language (default: ko)
    """
    if not translator.is_available():
        return (
            "[Info] Translation not available. Naver Papago API key is not configured.\n"
            "This is optional. To enable, add NAVER_CLIENT_ID and NAVER_CLIENT_SECRET to .env\n"
            "Get your free key at: https://developers.naver.com"
        )

    try:
        result = translator.translate(text, source, target)
    except Exception as e:
        return f"[Error] Translation failed: {e}"

    return f"## Translation ({source} -> {target})\n\n{result}"


# ──────────────────────────────────────────────
# Combined Research (killer feature)
# ──────────────────────────────────────────────

@mcp.tool()
def research_topic(topic: str, count: int = 5) -> str:
    """All-in-one academic research: papers + citations + BibTeX + translation.
    This is the main tool — generates a comprehensive research report.

    - topic: Research topic (e.g. 'reinforcement learning from human feedback')
    - count: Number of papers to include (default: 5)
    """
    sections = []
    sections.append(f"# Academic Research Report: {topic}\n")
    sections.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    sections.append("---\n")

    # 1. Latest papers from arXiv
    sections.append("## 1. Latest Papers (arXiv)\n")
    arxiv_papers = []
    try:
        arxiv_papers = arxiv.search_papers(topic, max_results=count)
        if arxiv_papers:
            for i, p in enumerate(arxiv_papers, 1):
                authors = ", ".join(p["authors"][:3])
                if len(p["authors"]) > 3:
                    authors += " et al."
                sections.append(f"  {i}. **{p['title']}**")
                sections.append(f"     {authors} ({p['published'][:10]})")
                sections.append(f"     {(p.get('abstract') or '')[:150]}...")
                sections.append(f"     PDF: {p['pdf_url']}")
                sections.append("")
        else:
            sections.append("  No papers found on arXiv.\n")
    except Exception as e:
        sections.append(f"  [Skipped] arXiv error: {e}\n")

    sections.append("---\n")

    # 2. Most cited papers from Semantic Scholar
    sections.append("## 2. Most Cited Papers (Semantic Scholar)\n")
    semantic_papers = []
    try:
        semantic_papers = semantic.search_papers(topic, limit=count)
        if semantic_papers:
            sorted_papers = sorted(
                semantic_papers,
                key=lambda x: x.get("citationCount", 0) or 0,
                reverse=True,
            )
            for i, p in enumerate(sorted_papers, 1):
                authors = ", ".join(p["authors"][:3])
                if len(p["authors"]) > 3:
                    authors += " et al."
                sections.append(f"  {i}. **{p['title']}**")
                sections.append(f"     {authors} ({p.get('year', 'N/A')})")
                sections.append(f"     Citations: {p.get('citationCount', 0)}")
                if p.get("doi"):
                    sections.append(f"     DOI: {p['doi']}")
                sections.append("")
        else:
            sections.append("  No papers found.\n")
    except Exception as e:
        sections.append(f"  [Skipped] Semantic Scholar error: {e}\n")

    sections.append("---\n")

    # 3. BibTeX citations
    sections.append("## 3. BibTeX Citations\n")
    sections.append("```bibtex")
    bibtex_count = 0
    all_papers = semantic_papers + [
        {"doi": None, "title": p["title"]} for p in arxiv_papers
    ]
    for p in all_papers:
        doi = p.get("doi")
        if doi and bibtex_count < 3:
            try:
                bib = crossref.get_bibtex(doi)
                sections.append(bib)
                sections.append("")
                bibtex_count += 1
            except Exception:
                continue
    if bibtex_count == 0:
        sections.append("% No BibTeX entries available (no DOIs found)")
    sections.append("```\n")

    sections.append("---\n")

    # 4. Korean translation of top abstract
    sections.append("## 4. Abstract Translation (Korean)\n")
    if translator.is_available():
        first_abstract = None
        first_title = None
        for p in arxiv_papers:
            if p.get("abstract"):
                first_abstract = p["abstract"][:500]
                first_title = p["title"]
                break
        if not first_abstract:
            for p in semantic_papers:
                if p.get("abstract"):
                    first_abstract = p["abstract"][:500]
                    first_title = p["title"]
                    break

        if first_abstract:
            try:
                translated = translator.translate(first_abstract)
                sections.append(f"  Paper: {first_title}\n")
                sections.append(f"  {translated}\n")
            except Exception as e:
                sections.append(f"  [Skipped] Translation error: {e}\n")
        else:
            sections.append("  No abstract available to translate.\n")
    else:
        sections.append("  [Skipped] Papago API not configured (optional).\n")
        sections.append("  To enable: add Naver API keys to .env\n")

    sections.append("---\n")
    sections.append("*Report generated by academic-research-mcp*")

    return "\n".join(sections)


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Academic Research MCP Server")
    parser.add_argument("--env", default="", help="Path to .env file")
    args = parser.parse_args()

    if args.env:
        from dotenv import load_dotenv
        load_dotenv(args.env)
        print(f"academic-research-mcp: loaded env from '{args.env}'", file=sys.stderr)
    else:
        from dotenv import load_dotenv
        from pathlib import Path
        load_dotenv(str(Path(__file__).parent / ".env"))

    print("academic-research-mcp: server starting", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
