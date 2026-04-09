# src/ingestion/pdf_extractor.py
import pymupdf  # PyMuPDF
from typing import List, Dict, Any

def table_to_markdown(table) -> str:
    """Convert table to markdown format (robust to None values)."""
    rows = table.extract()
    if not rows:
        return ""

    def clean_cell(cell):
        if cell is None:
            return ""
        return str(cell).strip()

    cleaned_rows = [
        [clean_cell(cell) for cell in row]
        for row in rows
    ]

    md = []

    header = cleaned_rows[0]
    md.append("| " + " | ".join(header) + " |")
    md.append("| " + " | ".join(["---"] * len(header)) + " |")

    for row in cleaned_rows[1:]:
        md.append("| " + " | ".join(row) + " |")

    return "\n".join(md)


def extract_pdf_raw(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract structured content from PDF.
    STRICT: preserves layout, tables, and unicode (Hindi safe).
    """

    doc = pymupdf.open(pdf_path)
    pages = []

    for page_num, page in enumerate(doc):
        raw_blocks = page.get_text("dict")["blocks"]
        text_blocks = sanitize_for_json(raw_blocks)
        
        tables = []

        # Table extraction (as per spec)
        if hasattr(page, "find_tables"):
            try:
                table_finder = page.find_tables()
                for table in table_finder.tables:
                    tables.append({
                        "bbox": table.bbox,
                        "cells": table.extract(),
                        "markdown": table_to_markdown(table)
                    })
            except Exception as e:
                print(f"[WARN] Table extraction failed on page {page_num+1}: {e}")

        pages.append({
            "page_number": page_num + 1,
            "text_blocks": text_blocks,
            "tables": tables
        })

    return pages


# HELPER FUNCTIONS
def sanitize_for_json(obj):
    """
    Recursively remove/convert non-serializable fields (bytes, etc.)
    while preserving structure.
    """
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            if isinstance(v, (bytes, bytearray)):
                # Drop binary fields completely
                continue
            clean[k] = sanitize_for_json(v)
        return clean

    elif isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]

    else:
        return obj