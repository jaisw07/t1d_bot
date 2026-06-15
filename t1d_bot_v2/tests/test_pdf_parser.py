import os
from src.ingestion.parsers.pdf_parser import PDFParser
from src.ingestion.parsers.base import DocumentPage

def test_pdf_parser_basic_extraction():
    # Arrange
    pdf_path = "dataset/ISPAD-English-2022/Ch1-DefinitionEpidemiol.pdf"
    assert os.path.exists(pdf_path), f"Test PDF file not found at {pdf_path}"
    
    parser = PDFParser()
    
    # Act
    pages = parser.parse(pdf_path, include_pages="1")
    
    # Assert
    assert len(pages) == 1
    page = pages[0]
    assert isinstance(page, DocumentPage)
    assert page.page_number == 1
    assert page.source_path == pdf_path
    assert len(page.text_blocks) > 0
    
    # Check that text blocks have content and formatting
    block = page.text_blocks[0]
    assert len(block.text.strip()) > 0
    assert block.font_size > 0
    assert isinstance(block.is_bold, bool)

def test_pdf_parser_page_filtering():
    pdf_path = "dataset/ISPAD-English-2022/Ch1-DefinitionEpidemiol.pdf"
    parser = PDFParser()
    
    # Act
    pages = parser.parse(pdf_path, include_pages="2-4")
    
    # Assert
    assert len(pages) == 3
    assert [p.page_number for p in pages] == [2, 3, 4]

