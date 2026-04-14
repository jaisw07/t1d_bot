from typing import List, Dict, Any
import re
import numpy as np


FORCED_SECTION_HEADINGS = {
    "CONFLICT OF INTEREST",
    "ORCID",
    "REFERENCES",
    "AUTHOR CONTRIBUTIONS",
    "PEER REVIEW",
    "DATA AVAILABILITY STATEMENT",
    "ACKNOWLEDGMENTS",
    "ACKNOWLEDGEMENTS",
    "FUNDING",
}


# -------------------------------
# STEP 1: LINE EXTRACTION
# -------------------------------

def extract_lines(pages: List[Dict[str, Any]]) -> List[Dict]:
    """Convert spans into full visual lines."""
    lines_out = []

    for page in pages:
        for block in page.get("text_blocks", []):
            for line in block.get("lines", []):

                spans = line.get("spans", [])
                if not spans:
                    continue

                text = " ".join(
                    span.get("text", "").strip()
                    for span in spans
                    if span.get("text", "").strip()
                ).strip()

                if not text:
                    continue

                avg_size = sum(span.get("size", 0) for span in spans) / len(spans)
                is_bold = any("Bold" in span.get("font", "") for span in spans)

                lines_out.append({
                    "text": text,
                    "size": avg_size,
                    "is_bold": is_bold,
                    "page": page["page_number"],
                    "span_count": len(spans)
                })

    return lines_out


# -------------------------------
# STEP 2: DOC STATS
# -------------------------------

def compute_doc_stats_from_lines(lines: List[Dict]) -> Dict[str, float]:
    """Compute font statistics."""
    sizes = [line["size"] for line in lines if line.get("size")]

    return {
        "p95_font_size": np.percentile(sizes, 95)
    }


# -------------------------------
# STEP 3: HEADING DETECTION
# -------------------------------

def is_heading(line: Dict, doc_stats: Dict) -> bool:
    text = line["text"].strip()
    upper = text.upper()

    # Force specific singleton headings that should always split sections.
    if upper in FORCED_SECTION_HEADINGS:
        return True

    # Keep keyword lines as their own heading even if they are not all-caps.
    if re.match(r"^K\s*E\s*Y\s*W\s*O\s*R\s*D\s*S\s*:", text, flags=re.IGNORECASE):
        return True

    # --- ORIGINAL RULES (preserved) ---
    base_rule = (
        line["size"] > doc_stats["p95_font_size"] or
        (line["is_bold"] and line["size"] > 14) or
        (text.isupper() and len(text) > 5)
    )

    if not base_rule:
        return False

    # --- FIXES FOR YOUR ISSUES ---

    # 1. Prevent word-by-word splitting
    if len(text.split()) <= 1:
        return False

    # 2. Remove author/reference name lines with trailing affiliation ids.
    if re.match(r"^[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){1,6}\s+\d+(?:,\d+)*$", text):
        return False

    # 2b. Remove compact acronym markers that often appear as inline labels.
    if re.fullmatch(r"[A-Z0-9-]{2,10}\s*\([A-Z]\)\.?", text):
        return False

    # 3. Remove bracket-led short fragments/noisy citation chunks.
    if text.startswith("("):
        if re.match(r"^\([^)]{1,40}\)(?:\.\s*[A-Z])?$", text):
            return False
        if any(ch.isdigit() for ch in text):
            return False

    # 4. Remove header/footer patterns
    if "ET AL" in upper:
        return False

    # 5. Avoid very long paragraph-like lines (not headings)
    if len(text.split()) > 20:
        return False

    return True


# -------------------------------
# STEP 4: CHAPTER DETECTION
# -------------------------------

def detect_chapters(pages: List[Dict[str, Any]]) -> List[Dict]:
    """
    Segment document into chapters based on detected headings.
    """

    lines = extract_lines(pages)
    doc_stats = compute_doc_stats_from_lines(lines)

    chapters = []
    current_chapter = None

    def same_page(idx_a: int, idx_b: int) -> bool:
        return lines[idx_a]["page"] == lines[idx_b]["page"]

    def line_text(idx: int) -> str:
        return lines[idx]["text"].strip()

    def is_numbered_section_marker(idx: int) -> bool:
        # Accept 3, 3.1, 3.2.1, etc.
        return bool(re.fullmatch(r"\d+(?:\.\d+)*", line_text(idx)))

    def is_standalone_bullet(idx: int) -> bool:
        return line_text(idx) == "•"

    def is_single_word_section_heading(idx: int) -> bool:
        # For numbered sections like 1 | INTRODUCTION
        t = line_text(idx)
        return bool(re.fullmatch(r"[A-Z][A-Z-]{2,}", t))

    def is_upper_fragment(idx: int) -> bool:
        """
        Allow safe wrapped all-caps continuation fragments (e.g. REGULATION),
        but reject noisy uppercase content.
        """
        t = line_text(idx)
        if not t or t in {"|", "•"} or t.isdigit():
            return False
        if "ET AL" in t.upper():
            return False
        if re.search(r"[()<>*/0-9]", t):
            return False
        if "." in t or ":" in t:
            return False
        if not t.isupper():
            return False
        words = t.split()
        # Do not allow single-word upper fragments here; those are only valid
        # in numbered-section context.
        if not (2 <= len(words) <= 4):
            return False
        return True

    def is_heading_like(idx: int) -> bool:
        return is_heading(lines[idx], doc_stats) or is_upper_fragment(idx)

    def is_forced_heading(idx: int) -> bool:
        return line_text(idx).upper() in FORCED_SECTION_HEADINGS

    def in_references_mode() -> bool:
        if not current_chapter:
            return False
        return current_chapter["title"].upper().endswith("REFERENCES")

    def looks_like_table_item(idx: int) -> bool:
        """
        Prevent table/list entries from becoming chapter titles.
        Handles bullet-adjacent lines and short uppercase/acronym rows inside TABLE chapters.
        """
        t = line_text(idx)

        # Always allow a true TABLE heading to start a new chapter.
        if re.fullmatch(r"TABLE\s+\d+[A-Z]?", t.upper()):
            return False

        prev_is_bullet = idx > 0 and same_page(idx - 1, idx) and is_standalone_bullet(idx - 1)
        next_is_bullet = idx + 1 < len(lines) and same_page(idx, idx + 1) and is_standalone_bullet(idx + 1)
        if prev_is_bullet or next_is_bullet:
            return True

        if current_chapter and current_chapter["title"].startswith("TABLE"):
            # INSR / HNF1A / short uppercase table-row items
            if re.fullmatch(r"[A-Z0-9-]{2,20}", t):
                return True
            if t.isupper() and len(t.split()) <= 4:
                return True

        return False

    def is_numbered_section_heading_token(idx: int) -> bool:
        # Token after N | can be normal heading or single-word uppercase heading.
        t = line_text(idx)

        # Also allow short title-case section labels (e.g., "Stages of T1D").
        title_case_like = (
            len(t.split()) <= 8
            and not t.endswith(".")
            and bool(re.search(r"[A-Za-z]", t))
            and not bool(re.search(r"[;:]", t))
        )

        return (
            is_heading_like(idx)
            or is_single_word_section_heading(idx)
            or title_case_like
        )

    def can_continue_heading(idx: int) -> bool:
        # Continuation can be normal heading-like or a single-word uppercase fragment.
        if is_heading_like(idx):
            return True
        if is_single_word_section_heading(idx):
            return True
        return False

    def can_continue_numbered_heading(start_idx: int, next_idx: int) -> bool:
        # Normal case: same-page continuation.
        if same_page(start_idx, next_idx):
            return can_continue_heading(next_idx)

        # Wrapped heading across page break when the previous token is a conjunction.
        if next_idx == 0:
            return False

        prev = line_text(next_idx - 1).upper()
        if lines[next_idx]["page"] == lines[next_idx - 1]["page"] + 1 and prev.endswith((" AND", " OR", " OF")):
            return is_single_word_section_heading(next_idx)

        return False

    i = 0
    while i < len(lines):
        text = line_text(i)

        # Keep references as one continuous section across page breaks.
        # This prevents citation lines from becoming random new headings.
        if in_references_mode() and not is_forced_heading(i):
            current_chapter["content"].append(text)
            i += 1
            continue

        # Merge numbered section markers: "2" + "|" + "HEADING"
        if (
            i + 2 < len(lines)
            and same_page(i, i + 1)
            and same_page(i, i + 2)
            and is_numbered_section_marker(i)
            and line_text(i + 1) == "|"
            and is_numbered_section_heading_token(i + 2)
        ):
            heading_parts = [line_text(i), "|", line_text(i + 2)]
            j = i + 3

            while j < len(lines) and can_continue_numbered_heading(i, j):
                if is_standalone_bullet(j):
                    break
                # Avoid TABLE-row false positives, but keep valid single-word
                # continuation tokens like "RECOMMENDATIONS".
                if looks_like_table_item(j) and not is_single_word_section_heading(j):
                    break
                heading_parts.append(line_text(j))
                j += 1

            heading_text = " ".join(heading_parts).strip()

            if current_chapter:
                chapters.append(current_chapter)

            current_chapter = {
                "title": heading_text,
                "content": [heading_text],
                "start_page": lines[i]["page"]
            }

            i = j
            continue

        # Normal heading start (never start from table-like items)
        if is_forced_heading(i) or (is_heading_like(i) and not looks_like_table_item(i)):
            heading_parts = [line_text(i)]
            j = i + 1

            # Merge wrapped heading lines on the same page.
            while j < len(lines) and same_page(i, j) and can_continue_heading(j):
                if is_standalone_bullet(j) or looks_like_table_item(j):
                    break
                heading_parts.append(line_text(j))
                j += 1

            heading_text = " ".join(heading_parts).strip()

            if current_chapter:
                chapters.append(current_chapter)

            current_chapter = {
                "title": heading_text,
                "content": [heading_text],
                "start_page": lines[i]["page"]
            }

            i = j
            continue

        if current_chapter:
            current_chapter["content"].append(text)

        i += 1

    if current_chapter:
        chapters.append(current_chapter)

    return chapters