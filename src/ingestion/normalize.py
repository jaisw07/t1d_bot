import json
import re
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter


# =========================================================
# CONFIG
# =========================================================

NOISE_PATTERNS = [
    r"DOI:",
    r"wileyonlinelibrary\.com",
    r"©\s?\d{4}",
    r"Accepted:",
    r"Received:",
    r"LIBMAN ET AL",
    r"ISPAD CLINICAL PRACTICE CONSENSUS GUIDELINES",
    r"^\d{3,4}$",  # isolated page numbers
]

BAD_TITLES = [
    "KEY WORDS",
    "TABLE",
    "FIGURE",
    "REFERENCES",
    "ORCID",
    "CONFLICT OF INTEREST",
    "AUTHOR CONTRIBUTIONS",
    "PEER REVIEW",
    "ACKNOWLEDGMENTS",
    "ACKNOWLEDGEMENTS",
]


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(text: str) -> str:
    """
    Conservative normalization.
    Does NOT overwrite source data.
    """

    if not text:
        return ""

    # Remove noise lines
    cleaned_lines = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        skip = False

        for pattern in NOISE_PATTERNS:
            if re.search(pattern, line, flags=re.IGNORECASE):
                skip = True
                break

        if not skip:
            cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    # Fix whitespace
    text = re.sub(r"\s+", " ", text)

    # Fix broken hyphenation
    text = re.sub(r"-\s+", "", text)

    return text.strip()


# =========================================================
# TITLE CLEANING
# =========================================================

def normalize_title(title: str) -> str:
    """
    Convert:
    '1 | INTRODUCTION'
    ->
    'Introduction'
    """

    if not title:
        return "Unknown"

    # Remove numbering
    title = re.sub(r"^\d+(\.\d+)?\s*\|\s*", "", title)

    # Normalize spacing
    title = re.sub(r"\s+", " ", title)

    # Title case
    title = title.strip().title()

    return title


# =========================================================
# CHAPTER ID
# =========================================================

def build_chapter_id(index: int) -> str:
    return f"ch{index:02d}"


# =========================================================
# CHUNK IDS
# =========================================================

def build_l2_id(chapter_id: str, chunk_idx: int) -> str:
    return f"{chapter_id}_l2_{chunk_idx:03d}"


def build_l3_id(chapter_id: str, l2_idx: int, l3_idx: int) -> str:
    return f"{chapter_id}_l3_{l2_idx:03d}_{l3_idx:03d}"


# =========================================================
# FILTERING
# =========================================================

def should_skip_title(title: str) -> bool:

    upper = title.upper()

    for bad in BAD_TITLES:
        if bad in upper:
            return True

    return False


# =========================================================
# LOADERS
# =========================================================

def load_json(path: Path):

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_chapter_title(l1_data: Any, chapter_index: int) -> str:

    if isinstance(l1_data, dict):
        return l1_data.get("title", f"Chapter {chapter_index}")

    if isinstance(l1_data, list):
        for item in l1_data:
            if isinstance(item, dict) and item.get("title"):
                return item["title"]

    return f"Chapter {chapter_index}"


# =========================================================
# NORMALIZE SINGLE CHAPTER
# =========================================================

def normalize_chapter(
    l1_data: Any,
    l2_data: List[Dict],
    l3_data: Dict,
    metadata_data: List[Dict],
    document_name: str,
    chapter_index: int,
) -> List[Dict]:

    normalized_rows = []

    chapter_id = build_chapter_id(chapter_index)

    chapter_title = normalize_title(
        extract_chapter_title(l1_data, chapter_index)
    )

    # -----------------------------------------------------
    # Metadata lookup
    # -----------------------------------------------------

    metadata_lookup = {
        x["chunk_id"]: x.get("metadata", {})
        for x in metadata_data
    }

    # -----------------------------------------------------
    # L3 lookup grouped by parent
    # -----------------------------------------------------

    l3_lookup = {}

    for l3 in l3_data.get("l3_chunks", []):

        parent = l3.get("parent_id")

        if parent not in l3_lookup:
            l3_lookup[parent] = []

        l3_lookup[parent].append(l3)

    # -----------------------------------------------------
    # Build normalized retrieval rows
    # -----------------------------------------------------

    for l2_idx, l2 in enumerate(l2_data, start=1):

        old_l2_id = l2["chunk_id"]

        new_l2_id = build_l2_id(chapter_id, l2_idx)

        cleaned_l2_text = clean_text(l2["text"])

        if not cleaned_l2_text:
            continue

        row_l2 = {
            "retrieval_id": new_l2_id,
            "chunk_level": "L2",

            "content": {
                "text": cleaned_l2_text,
                "token_estimate": len(cleaned_l2_text.split())
            },

            "hierarchy": {
                "document": document_name,
                "chapter_id": chapter_id,
                "chapter_title": chapter_title,
                "parent_id": chapter_id,
                "child_ids": [],
            },

            "source": {
                "start_page": l2.get("start_page"),
                "section_title": chapter_title,
            },

            "metadata": metadata_lookup.get(old_l2_id, {}),

            "retrieval": {
                "embedding_ready": True,
                "preferred_for_context": True,
                "retrieval_weight": 1.0,
            }
        }

        # -------------------------------------------------
        # L3 rows
        # -------------------------------------------------

        l3_children = l3_lookup.get(old_l2_id, [])

        child_ids = []

        for l3_idx, l3 in enumerate(l3_children, start=1):

            new_l3_id = build_l3_id(
                chapter_id,
                l2_idx,
                l3_idx
            )

            child_ids.append(new_l3_id)

            cleaned_l3_text = clean_text(l3["text"])

            if not cleaned_l3_text:
                continue

            row_l3 = {
                "retrieval_id": new_l3_id,
                "chunk_level": "L3",

                "content": {
                    "text": cleaned_l3_text,
                    "token_estimate": len(cleaned_l3_text.split())
                },

                "hierarchy": {
                    "document": document_name,
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title,
                    "parent_id": new_l2_id,
                    "child_ids": [],
                },

                "source": {
                    "start_page": l2.get("start_page"),
                    "section_title": chapter_title,
                },

                # inherit metadata from L2
                "metadata": metadata_lookup.get(old_l2_id, {}),

                "retrieval": {
                    "embedding_ready": True,
                    "preferred_for_context": False,
                    "retrieval_weight": 0.85,
                }
            }

            normalized_rows.append(row_l3)

        row_l2["hierarchy"]["child_ids"] = child_ids

        normalized_rows.append(row_l2)

    return normalized_rows


# =========================================================
# FULL DATASET NORMALIZATION
# =========================================================

def normalize_dataset(
    chapters_dir: str,
    chunks_dir: str,
    atoms_dir: str,
    metadata_dir: str,
    output_path: str,
    document_name: str = "ISPAD_2022",
):

    chapters_dir = Path(chapters_dir)
    chunks_dir = Path(chunks_dir)
    atoms_dir = Path(atoms_dir)
    metadata_dir = Path(metadata_dir)

    all_rows = []

    chapter_files = sorted(chapters_dir.glob("*.json"))

    print(f"[INFO] Found {len(chapter_files)} chapters")

    for idx, l1_file in enumerate(chapter_files, start=1):

        stem = l1_file.stem

        print(f"\n[PROCESSING] {stem}")

        l2_file = chunks_dir / f"{stem}.json"
        l3_file = atoms_dir / f"{stem}.json"
        meta_file = metadata_dir / f"{stem}.json"

        if not (
            l2_file.exists()
            and l3_file.exists()
            and meta_file.exists()
        ):
            print(f"[WARNING] Missing files for {stem}")
            continue

        # ---------------------------------------------
        # Load
        # ---------------------------------------------

        l1_data = load_json(l1_file)
        l2_data = load_json(l2_file)

        l3_data = load_json(l3_file)

        metadata_data = load_json(meta_file)

        # ---------------------------------------------
        # Skip noisy chapters
        # ---------------------------------------------

        title = extract_chapter_title(l1_data, idx)

        if should_skip_title(title):
            print(f"[SKIP] {title}")
            continue

        # ---------------------------------------------
        # Normalize
        # ---------------------------------------------

        rows = normalize_chapter(
            l1_data=l1_data,
            l2_data=l2_data,
            l3_data=l3_data,
            metadata_data=metadata_data,
            document_name=document_name,
            chapter_index=idx,
        )

        all_rows.extend(rows)

    # =================================================
    # Deduplicate retrieval IDs
    # =================================================

    ids = [x["retrieval_id"] for x in all_rows]

    duplicates = [
        k for k, v in Counter(ids).items()
        if v > 1
    ]

    if duplicates:
        raise ValueError(
            f"Duplicate retrieval IDs found: {duplicates[:5]}"
        )

    # =================================================
    # Save JSONL
    # =================================================

    output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:

        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("\n=================================================")
    print(f"[DONE] Normalized corpus saved")
    print(f"[PATH] {output_path}")
    print(f"[ROWS] {len(all_rows)}")

    # =================================================
    # Stats
    # =================================================

    l2_count = sum(
        1 for x in all_rows
        if x["chunk_level"] == "L2"
    )

    l3_count = sum(
        1 for x in all_rows
        if x["chunk_level"] == "L3"
    )

    print("\n[STATS]")
    print(f"L2 chunks: {l2_count}")
    print(f"L3 chunks: {l3_count}")

    return all_rows