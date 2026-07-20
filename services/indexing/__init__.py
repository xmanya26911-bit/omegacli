"""
Ω OMEGA Indexing Service — Background indexing for repos, conversations, files (§384).

Provides interfaces for text extraction, chunking, embedding,
and vector storage. Designed for async batch processing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ── Types ──────────────────────────────────────────────────────────────────

class IndexStatus(Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class IndexType(Enum):
    FILE = "file"
    CONVERSATION = "conversation"
    REPOSITORY = "repository"
    DOCUMENT = "document"


@dataclass
class IndexItem:
    """A single item to be indexed."""
    id: str
    index_type: IndexType
    source: str  # File path, conversation ID, repo URL
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    status: IndexStatus = IndexStatus.PENDING
    error: Optional[str] = None
    chunk_count: int = 0


# ── Document Processor ─────────────────────────────────────────────────────

class DocumentProcessor:
    """Extract text from various document formats."""

    SUPPORTED_EXTENSIONS: set[str] = {
        ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx",
        ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
        ".html", ".css", ".scss", ".sql",
    }

    def can_handle(self, path: str) -> bool:
        """Check if this processor can handle the given file."""
        import os
        ext = os.path.splitext(path)[1].lower()
        return ext in self.SUPPORTED_EXTENSIONS

    def extract_text(self, content: str, path: str) -> str:
        """Extract meaningful text from raw content."""
        # Basic extraction — no-op for text formats
        return content

    def chunk(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        return chunks


# ── Indexer ────────────────────────────────────────────────────────────────

class Indexer:
    """Manages the indexing queue and processing."""

    def __init__(self):
        self._items: dict[str, IndexItem] = {}
        self._processor = DocumentProcessor()

    def add_item(self, item: IndexItem) -> str:
        """Add an item to the index queue."""
        self._items[item.id] = item
        return item.id

    def add_file(self, path: str, content: str, metadata: Optional[dict] = None) -> Optional[str]:
        """Convenience: add a file for indexing."""
        import uuid
        if not self._processor.can_handle(path):
            return None
        item = IndexItem(
            id=f"idx-{uuid.uuid4().hex[:12]}",
            index_type=IndexType.FILE,
            source=path,
            content=content,
            metadata=metadata or {},
        )
        return self.add_item(item)

    def process(self, item_id: str) -> list[str]:
        """Process a single item — extract text and chunk."""
        item = self._items.get(item_id)
        if not item:
            return []

        try:
            item.status = IndexStatus.INDEXING
            text = self._processor.extract_text(item.content, item.source)
            chunks = self._processor.chunk(text)
            item.chunk_count = len(chunks)
            item.status = IndexStatus.COMPLETED
            return chunks
        except Exception as e:
            item.status = IndexStatus.FAILED
            item.error = str(e)
            return []

    def get_item(self, item_id: str) -> Optional[IndexItem]:
        return self._items.get(item_id)

    def pending_count(self) -> int:
        return sum(1 for i in self._items.values() if i.status == IndexStatus.PENDING)

    @property
    def items(self) -> dict[str, IndexItem]:
        return dict(self._items)
