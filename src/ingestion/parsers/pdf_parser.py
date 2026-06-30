import pymupdf
from .base import DocumentParser, DocumentPage, TextBlock
from src.ingestion.krutidev import krutidev_to_unicode, has_devanagari, is_likely_krutidev

def parse_page_range(page_range_str: str | None, max_pages: int) -> set[int]:
    """Parse range string like '1-5,7,10-12' into 1-based page numbers."""
    if not page_range_str or page_range_str.strip() == "" or page_range_str.strip().upper() == "TBD":
        return set(range(1, max_pages + 1))
    
    pages = set()
    for part in page_range_str.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            try:
                start, end = part.split('-')
                start_val = int(start.strip())
                if end.strip().upper() == "TBD" or not end.strip():
                    end_val = max_pages
                else:
                    end_val = int(end.strip())
                pages.update(range(start_val, end_val + 1))
            except ValueError:
                pass
        else:
            try:
                pages.add(int(part))
            except ValueError:
                pass
    return pages

def table_to_markdown(table) -> str:
    """Convert PyMuPDF table to markdown format."""
    rows = table.extract()
    if not rows:
        return ""

    def clean_cell(cell):
        if cell is None:
            return ""
        return str(cell).strip().replace("\n", " ")

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

class PDFParser(DocumentParser):
    def parse(self, path: str, include_pages: str | None = None, language: str = "english") -> list[DocumentPage]:
        doc = pymupdf.open(path)
        max_pages = len(doc)
        pages_to_include = parse_page_range(include_pages, max_pages)
        
        pages_out = []
        for page_idx in sorted(list(pages_to_include)):
            if page_idx < 1 or page_idx > max_pages:
                continue
            
            page = doc[page_idx - 1]
            text_blocks = []
            
            # Extract text blocks
            try:
                raw_blocks = page.get_text("dict")["blocks"]
                for block in raw_blocks:
                    if block.get("type") == 0:  # Text block
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
                            bbox = line.get("bbox")
                            
                            text_blocks.append(TextBlock(
                                text=text,
                                font_size=avg_size,
                                is_bold=is_bold,
                                bbox=bbox
                            ))
            except Exception as e:
                print(f"[WARN] Text extraction failed on page {page_idx}: {e}")
                
            # Extract simple tables using PyMuPDF native support
            tables_out = []
            if hasattr(page, "find_tables"):
                try:
                    table_finder = page.find_tables()
                    for table in table_finder.tables:
                        md_table = table_to_markdown(table)
                        if md_table:
                            tables_out.append(md_table)
                except Exception as e:
                    print(f"[WARN] Table extraction failed on page {page_idx}: {e}")
            
            # Page-level KrutiDev or scrambled Devanagari conversion for Hindi
            if language == "hindi":
                all_text = " ".join(b.text for b in text_blocks)
                if not has_devanagari(all_text) and is_likely_krutidev(all_text):
                    for b in text_blocks:
                        b.text = krutidev_to_unicode(b.text)
                    tables_out = [krutidev_to_unicode(t) for t in tables_out]
                else:
                    from src.ingestion.hindi_decoder import is_scrambled_hindi, decode_hindi_text
                    if is_scrambled_hindi(all_text):
                        for b in text_blocks:
                            b.text = decode_hindi_text(b.text)
                        tables_out = [decode_hindi_text(t) for t in tables_out]

            pages_out.append(DocumentPage(
                page_number=page_idx,
                text_blocks=text_blocks,
                tables=tables_out,
                source_path=path
            ))
            
        doc.close()
        return pages_out
