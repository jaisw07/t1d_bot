from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class TextBlock:
    text: str
    font_size: float
    is_bold: bool
    bbox: tuple[float, float, float, float] | None = None

@dataclass
class DocumentPage:
    page_number: int
    text_blocks: list[TextBlock]
    tables: list[str]
    source_path: str

class DocumentParser(ABC):
    @abstractmethod
    def parse(self, path: str, include_pages: str | None = None, language: str = "english") -> list[DocumentPage]:
        pass
