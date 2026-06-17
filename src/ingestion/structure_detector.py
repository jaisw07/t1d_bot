from dataclasses import dataclass
import numpy as np
from .parsers.base import DocumentPage, TextBlock

@dataclass
class Section:
    title: str
    level: int
    start_page: int
    end_page: int
    content: list[str]

class StructureDetector:
    def detect(self, pages: list[DocumentPage]) -> list[Section]:
        if not pages:
            return []
            
        # Collect all font sizes to calculate median and p90
        sizes = [b.font_size for p in pages for b in p.text_blocks if b.font_size > 0]
        if sizes:
            median_size = float(np.median(sizes))
            p90_size = float(np.percentile(sizes, 90))
        else:
            median_size = 11.0
            p90_size = 14.0
            
        sections = []
        current_title = "Introduction"
        current_content = []
        start_page = pages[0].page_number
        current_level = 1
        
        def is_heading(block: TextBlock) -> bool:
            text = block.text.strip()
            if not text or not any(c.isalnum() for c in text):
                return False
                
            # Heuristics:
            # 1. Font size significantly above median
            if block.font_size >= median_size + 3.0:
                return True
            # 2. Font size is above median, bold, and not too long
            if block.is_bold and block.font_size >= median_size + 1.0:
                if len(text.split()) < 20:
                    return True
            # 3. All uppercase, bold, and not too long (typical section heading)
            if text.isupper() and block.is_bold and len(text.split()) < 12:
                return True
            return False

        for page in pages:
            for block in page.text_blocks:
                if is_heading(block):
                    # Save the previous section if we have accumulated content or a real heading
                    if current_content or current_title != "Introduction":
                        sections.append(Section(
                            title=current_title,
                            level=current_level,
                            start_page=start_page,
                            end_page=page.page_number,
                            content=current_content
                        ))
                    
                    # Start new section
                    current_title = block.text.strip()
                    current_content = []
                    start_page = page.page_number
                    
                    # Determine level
                    if block.font_size >= p90_size:
                        current_level = 1
                    else:
                        current_level = 2
                else:
                    current_content.append(block.text.strip())
                    
        # Append final section
        if current_content or current_title != "Introduction":
            end_page = pages[-1].page_number
            sections.append(Section(
                title=current_title,
                level=current_level,
                start_page=start_page,
                end_page=end_page,
                content=current_content
            ))
            
        return sections
