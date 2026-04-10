"""Multi-page PDF/TXT heading detection from plain text (no Word styles)."""

from __future__ import annotations

from vantage_preprocess.models.document import PageText
from vantage_preprocess.sections.models import DocumentSection, HeadingSource
from vantage_preprocess.sections.patterns import (
    heading_noise_thresholds,
    min_heading_score,
    score_line_as_heading,
)
from vantage_preprocess.utils.text import normalize_whitespace


def _lines_with_pages(pages: list[PageText]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for pg in pages:
        for line in pg.text.split("\n"):
            out.append((pg.page_number, line))
    return out


def _span_pages(rows: list[tuple[int, str]], start: int, end: int) -> tuple[int, int]:
    """Inclusive ``start``/``end`` indices into ``rows``."""
    if start > end or not rows:
        return 1, 1
    pages = [rows[i][0] for i in range(start, end + 1)]
    return min(pages), max(pages)


def _nonempty_count(rows: list[tuple[int, str]]) -> int:
    return sum(1 for _, ln in rows if ln.strip())


def _total_chars(pages: list[PageText]) -> int:
    return sum(len(p.text) for p in pages)


def sections_from_page_text_heuristic(
    pages: list[PageText],
) -> tuple[list[DocumentSection], str, list[str]]:
    """
    Detect headings from line patterns; may fall back to one section per page or one for whole doc.

    Returns ``(sections, strategy, notes)`` where ``strategy`` is
    ``text_heuristic`` | ``fallback_page`` | ``fallback_single``.
    """
    notes: list[str] = [
        "PDF/TXT: headings inferred from line patterns (CSI PART/SECTION, numbered outlines, …).",
    ]
    if not pages:
        return [], "fallback_single", notes + ["No pages; empty result."]

    rows = _lines_with_pages(pages)
    min_score = min_heading_score()
    frac_limit, count_limit = heading_noise_thresholds()

    scores: list[float | None] = []
    for _pg, ln in rows:
        hs = score_line_as_heading(ln)
        scores.append(hs.score if hs else None)

    candidate_idx = [i for i, sc in enumerate(scores) if sc is not None and sc >= min_score]
    nonempty = _nonempty_count(rows)

    too_many = len(candidate_idx) > count_limit or (
        nonempty > 50 and len(candidate_idx) > max(15, int(nonempty * frac_limit))
    )

    if too_many:
        notes.append(
            "Fallback: too many heading-like lines (possible TOC/forms noise); "
            "using one section per page.",
        )
        return _fallback_per_page(pages), "fallback_page", notes

    if not candidate_idx:
        total = _total_chars(pages)
        if total < 400:
            notes.append("Short document with no heading patterns; single section.")
        else:
            notes.append("No strong heading lines; merged into one section (fallback).")
        body = normalize_whitespace("\n\n".join(p.text for p in pages))
        ps, pe = pages[0].page_number, pages[-1].page_number
        sec = DocumentSection(
            section_index=0,
            heading_text=None,
            body_text=body,
            page_start=ps,
            page_end=pe,
            heading_source=HeadingSource.FALLBACK_SINGLE,
            confidence=0.4,
            reasons=["No line met the construction heading threshold."],
        )
        return [sec], "fallback_single", notes

    sections = _split_on_candidates(rows, scores, candidate_idx)
    return sections, "text_heuristic", notes


def _fallback_per_page(pages: list[PageText]) -> list[DocumentSection]:
    out: list[DocumentSection] = []
    for i, pg in enumerate(pages):
        body = normalize_whitespace(pg.text)
        out.append(
            DocumentSection(
                section_index=i,
                heading_text=None,
                body_text=body,
                page_start=pg.page_number,
                page_end=pg.page_number,
                heading_source=HeadingSource.FALLBACK_PAGE,
                confidence=0.35,
                reasons=["Page-level segment (heading heuristics unreliable)."],
            ),
        )
    return out


def _split_on_candidates(
    rows: list[tuple[int, str]],
    scores: list[float | None],
    candidate_idx: list[int],
) -> list[DocumentSection]:
    """Build sections between heading lines; preamble before first heading is allowed."""
    sections: list[DocumentSection] = []
    first_h = candidate_idx[0]

    if first_h > 0:
        preamble_lines = [rows[i][1] for i in range(0, first_h)]
        body = normalize_whitespace("\n".join(preamble_lines))
        if body.strip():
            ps, pe = _span_pages(rows, 0, first_h - 1)
            sections.append(
                DocumentSection(
                    section_index=len(sections),
                    heading_text=None,
                    body_text=body,
                    page_start=ps,
                    page_end=pe,
                    heading_source=HeadingSource.PATTERN,
                    confidence=0.5,
                    reasons=["Preamble before first detected heading."],
                ),
            )

    for ci, cidx in enumerate(candidate_idx):
        title = rows[cidx][1].strip()
        sc = scores[cidx] or 0.0
        body_start = cidx + 1
        body_end = (
            candidate_idx[ci + 1] - 1 if ci + 1 < len(candidate_idx) else len(rows) - 1
        )
        if body_start > body_end:
            body_text = ""
        else:
            body_lines = [rows[i][1] for i in range(body_start, body_end + 1)]
            body_text = normalize_whitespace("\n".join(body_lines))
        ps, pe = _span_pages(rows, cidx, body_end if body_start <= body_end else cidx)
        hs = score_line_as_heading(title)
        detail = list(hs.reasons) if hs else ["Heuristic heading boundary."]
        sections.append(
            DocumentSection(
                section_index=len(sections),
                heading_text=title,
                body_text=body_text,
                page_start=ps,
                page_end=pe,
                heading_source=HeadingSource.PATTERN,
                confidence=min(0.95, 0.55 + sc / 20.0),
                reasons=detail,
            ),
        )

    return sections
