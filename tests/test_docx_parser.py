import os
from src.ingestion.parsers.docx_parser import DocxParser
from src.ingestion.parsers.base import DocumentPage

def test_docx_parser_basic_extraction():
    # Arrange
    docx_path = "dataset/diabetes education full for ward  18.8.15.docx"
    assert os.path.exists(docx_path), f"Test DOCX file not found at {docx_path}"
    
    parser = DocxParser()
    
    # Act
    pages = parser.parse(docx_path)
    
    # Assert
    assert len(pages) >= 1
    page = pages[0]
    assert isinstance(page, DocumentPage)
    assert page.page_number == 1
    assert page.source_path == docx_path
    assert len(page.text_blocks) > 0
    
    # Let's verify we extracted text
    text_content = " ".join(block.text for block in page.text_blocks)
    assert "DIABETES" in text_content.upper()
