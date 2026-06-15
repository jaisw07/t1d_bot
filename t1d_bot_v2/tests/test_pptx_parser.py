import os
from src.ingestion.parsers.pptx_parser import PptxParser
from src.ingestion.parsers.base import DocumentPage

def test_pptx_parser_basic_extraction():
    # Arrange
    pptx_path = "dataset/DSMES Modules/Admission and Discharge teaching.pptx"
    assert os.path.exists(pptx_path), f"Test PPTX file not found at {pptx_path}"
    
    parser = PptxParser()
    
    # Act
    pages = parser.parse(pptx_path)
    
    # Assert
    assert len(pages) >= 1
    page = pages[0]
    assert isinstance(page, DocumentPage)
    assert page.page_number == 1
    assert page.source_path == pptx_path
    assert len(page.text_blocks) > 0
    
    # Let's verify we extracted text
    text_content = " ".join(block.text for block in page.text_blocks)
    assert len(text_content.strip()) > 0
