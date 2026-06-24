from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class BoothInfo(BaseModel):
    name: str = ""
    description: str = ""


class CompanionProfile(BaseModel):
    name: str = ""
    role: str = ""


class ExhibitItem(BaseModel):
    id: str
    title: str
    summary: str
    details: str = ""
    links: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class ExhibitCatalog(BaseModel):
    id: str = ""
    keywords: list[str] = Field(default_factory=list)
    booth: BoothInfo = Field(default_factory=BoothInfo)
    companion: CompanionProfile = Field(default_factory=CompanionProfile)
    exhibits: list[ExhibitItem] = Field(default_factory=list)


class ExhibitCatalogLoader:
    def __init__(self, base_path: Path | None = None) -> None:
        self._base_path = base_path or Path.cwd()

    def load(self, catalog_path: str) -> ExhibitCatalog:
        path = Path(catalog_path)
        if not path.is_absolute():
            path = self._base_path / path
        with path.open("r", encoding="utf-8") as file:
            raw_catalog = yaml.safe_load(file) or {}
        return ExhibitCatalog.model_validate(raw_catalog)

    def load_many(self, catalog_paths: list[str]) -> list[ExhibitCatalog]:
        return [self.load(catalog_path) for catalog_path in catalog_paths]
