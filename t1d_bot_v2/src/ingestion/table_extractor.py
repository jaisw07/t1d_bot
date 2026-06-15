from .parsers.base import DocumentPage

class TableExtractor:
    def extract_tables(self, pages: list[DocumentPage]) -> list[DocumentPage]:
        """
        Processes document pages to extract tables.
        Currently operates as a pass-through because the parsers (PDF, DOCX, PPTX)
        already extract native/simple tables and format them into markdown.
        
        Can be extended with vision-augmented fallback in the future:
        - Identify pages containing complex/unextracted tables
        - Crop table bounding box regions
        - Pass cropped images to Ollama vision client for markdown conversion
        """
        # Pass-through for now, as simple table extraction is done at parse-time.
        return pages
