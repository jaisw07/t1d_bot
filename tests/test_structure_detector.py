import os
from src.ingestion.parsers.pdf_parser import PDFParser
from src.ingestion.structure_detector import StructureDetector, Section

def test_structure_detector_pdf_pages():
    # Arrange
    pdf_path = "dataset/guidelines/ispad_2022/Ch1-DefinitionEpidemiol.pdf"
    assert os.path.exists(pdf_path)
    
    parser = PDFParser()
    pages = parser.parse(pdf_path, include_pages="1-3")
    
    # Act
    detector = StructureDetector()
    sections = detector.detect(pages)
    
    # Assert
    assert len(sections) > 0
    first_section = sections[0]
    assert isinstance(first_section, Section)
    assert first_section.start_page == 1
    assert len(first_section.title) > 0
    assert len(first_section.content) > 0
    
    # Check that it groups paragraphs logically
    # The title should be in upper case or bold/larger font
    assert first_section.level >= 1
