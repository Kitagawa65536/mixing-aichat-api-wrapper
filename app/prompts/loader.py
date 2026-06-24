from __future__ import annotations

from pathlib import Path


class PromptLoader:
    def __init__(self, base_path: Path | None = None) -> None:
        self._base_path = base_path or Path.cwd()

    def load(self, prompt_path: str) -> str:
        path = Path(prompt_path)
        if not path.is_absolute():
            path = self._base_path / path
        return path.read_text(encoding="utf-8")
