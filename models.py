from typing import List
from dataclasses import dataclass, field

# TODO tag the crawled files with respective accounts it belongs to
@dataclass
class Account:
    bank: str
    account_number: str
    name: str
    cards: List[str]

@dataclass(slots=True)
class CrawledFile:
    filepath: str
    extension: str
    size: int
    crawl_date: str
    # Unified metadata approach
    metadata: dict = field(default_factory=dict)
    
    # Computed properties
    @property
    def filename(self) -> str:
        return self.filepath.split('/')[-1]

    @property
    def is_readable(self) -> bool:
        return os.access(self.filepath, os.R_OK)
    
    @property
    def file_type(self) -> str:
        return self.extension.lower()
