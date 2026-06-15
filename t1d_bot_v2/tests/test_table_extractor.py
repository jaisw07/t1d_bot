from src.ingestion.parsers.base import DocumentPage, TextBlock
from src.ingestion.table_extractor import TableExtractor

def test_table_extractor_passthrough():
    # Arrange
    pages = [
        DocumentPage(
            page_number=1,
            text_blocks=[TextBlock(text="Some text", font_size=11.0, is_bold=False)],
            tables=["| Header 1 | Header 2 |\n|---|---|\n| Cell 1 | Cell 2 |"],
            source_path="dummy.pdf"
        )
    ]
    
    extractor = TableExtractor()
    
    # Act
    processed_pages = extractor.extract_tables(pages)
    
    # Assert
    assert len(processed_pages) == 1
    assert processed_pages[0].tables == pages[0].tables
    assert processed_pages[0].text_blocks == pages[0].text_blocks
