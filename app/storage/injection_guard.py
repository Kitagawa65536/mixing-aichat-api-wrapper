from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from app.models.chat import ChatCompletionRequest, ChatMessage


class InjectionPromptStore:
    def __init__(
        self,
        db_path: str | Path,
        *,
        max_entries: int,
        min_prompt_chars: int,
        mask_text: str,
    ) -> None:
        self._db_path = Path(db_path)
        self._max_entries = max_entries
        self._min_prompt_chars = min_prompt_chars
        self._mask_text = mask_text
        self._cached_prompts: list[str] | None = None

    def sanitize_request(self, request: ChatCompletionRequest) -> ChatCompletionRequest:
        prompts = self._load_prompts()
        if not prompts:
            return request

        messages: list[ChatMessage] = []
        changed = False
        for message in request.messages:
            content, content_changed = self._sanitize_content(message.content, prompts)
            if content_changed:
                changed = True
                messages.append(message.model_copy(update={"content": content}))
            else:
                messages.append(message)

        if not changed:
            return request
        return request.model_copy(update={"messages": messages})

    def add_prompt(self, prompt: str | None) -> bool:
        normalized = self._normalize_prompt(prompt)
        if normalized is None:
            return False

        self._ensure_schema()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO injection_prompts (prompt, created_at)
                VALUES (?, ?)
                """,
                (normalized, time.time()),
            )
            self._prune_old_prompts(connection)

        self._cached_prompts = None
        return True

    def _sanitize_content(
        self,
        content: str | list[dict[str, Any]] | None,
        prompts: list[str],
    ) -> tuple[str | list[dict[str, Any]] | None, bool]:
        if isinstance(content, str):
            sanitized = self._sanitize_text(content, prompts)
            return sanitized, sanitized != content

        if isinstance(content, list):
            sanitized_parts: list[dict[str, Any]] = []
            changed = False
            for part in content:
                sanitized_part = dict(part)
                text = sanitized_part.get("text")
                if isinstance(text, str):
                    sanitized_text = self._sanitize_text(text, prompts)
                    if sanitized_text != text:
                        sanitized_part["text"] = sanitized_text
                        changed = True
                sanitized_parts.append(sanitized_part)
            return sanitized_parts if changed else content, changed

        return content, False

    def _sanitize_text(self, text: str, prompts: list[str]) -> str:
        sanitized = text
        for prompt in prompts:
            sanitized = sanitized.replace(prompt, self._mask_text)
        return sanitized

    def _load_prompts(self) -> list[str]:
        if self._cached_prompts is not None:
            return self._cached_prompts

        self._ensure_schema()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT prompt FROM injection_prompts ORDER BY length(prompt) DESC, created_at DESC"
            ).fetchall()
        self._cached_prompts = [row[0] for row in rows]
        return self._cached_prompts

    def _normalize_prompt(self, prompt: str | None) -> str | None:
        if prompt is None:
            return None
        normalized = prompt.strip()
        if len(normalized) < self._min_prompt_chars:
            return None
        return normalized

    def _prune_old_prompts(self, connection: sqlite3.Connection) -> None:
        old_prompts = connection.execute(
            """
            SELECT prompt FROM injection_prompts
            ORDER BY created_at DESC
            LIMIT -1 OFFSET ?
            """,
            (self._max_entries,),
        ).fetchall()
        if not old_prompts:
            return

        connection.executemany(
            "DELETE FROM injection_prompts WHERE prompt = ?",
            old_prompts,
        )

    def _ensure_schema(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS injection_prompts (
                    prompt TEXT PRIMARY KEY,
                    created_at REAL NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)
