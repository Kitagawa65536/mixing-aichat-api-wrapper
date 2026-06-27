from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class CharacterMemoryItem(BaseModel):
    id: str
    title: str
    summary: str
    details: str = ""
    keywords: list[str] = Field(default_factory=list)


class CharacterMemoryCatalog(BaseModel):
    id: str = ""
    keywords: list[str] = Field(default_factory=list)
    memories: list[CharacterMemoryItem] = Field(default_factory=list)


class CharacterMemoryLoader:
    def __init__(self, base_path: Path | None = None) -> None:
        self._base_path = base_path or Path.cwd()

    def load(self, memory_path: str) -> CharacterMemoryCatalog:
        path = Path(memory_path)
        if not path.is_absolute():
            path = self._base_path / path
        with path.open("r", encoding="utf-8") as file:
            raw_memory = yaml.safe_load(file) or {}
        return CharacterMemoryCatalog.model_validate(raw_memory)

    def load_many(self, memory_paths: list[str]) -> list[CharacterMemoryCatalog]:
        return [self.load(memory_path) for memory_path in memory_paths]
