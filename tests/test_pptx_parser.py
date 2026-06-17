import os
from src.ingestion.parsers.pptx_parser import PptxParser
from src.ingestion.parsers.base import DocumentPage
from src.ingestion.krutidev import has_devanagari

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

def test_pptx_parser_hindi_english_slide_not_corrupted():
    """Slide 1 is English — should not be converted even with language=hindi."""
    parser = PptxParser()
    pages = parser.parse("dataset/DSMES Modules/Admission and Discharge teaching.pptx", language="hindi")
    slide1 = pages[0]
    text = " ".join(b.text for b in slide1.text_blocks)
    assert "Admission" in text
    assert not has_devanagari(text)

def test_pptx_parser_hindi_unicode_slides_preserved():
    """Slides 2, 7, 21, 25 are native Unicode Hindi — should not be corrupted."""
    parser = PptxParser()
    pages = parser.parse("dataset/DSMES Modules/Admission and Discharge teaching.pptx", language="hindi")
    for slide_num in [2, 7, 21, 25]:
        slide = pages[slide_num - 1]
        text = " ".join(b.text for b in slide.text_blocks)
        assert has_devanagari(text), f"Slide {slide_num} should have Devanagari"

def test_pptx_parser_hindi_empty_slides_no_crash():
    """Slides 16-19 are empty — should not crash with language=hindi."""
    parser = PptxParser()
    pages = parser.parse("dataset/DSMES Modules/Admission and Discharge teaching.pptx", language="hindi")
    for slide_num in [16, 17, 18, 19]:
        slide = pages[slide_num - 1]
        assert len(slide.text_blocks) == 0

