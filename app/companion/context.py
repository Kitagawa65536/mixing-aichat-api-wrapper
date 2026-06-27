from __future__ import annotations

import re

from app.companion.catalog import ExhibitCatalog
from app.companion.memory import CharacterMemoryCatalog, CharacterMemoryItem
from app.models.chat import ChatCompletionRequest, ChatMessage


TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u3040-\u30ff\u3400-\u9fff]+")


class CompanionContextBuilder:
    def build(
        self,
        persona_prompt: str,
        catalog: ExhibitCatalog,
        memories: list[CharacterMemoryItem] | None = None,
    ) -> str:
        sections = [
            persona_prompt.strip(),
            self._build_booth_section(catalog),
            self._build_exhibit_section(catalog),
            self._build_memory_section(memories or []),
        ]
        return "\n\n".join(section for section in sections if section)

    def _build_booth_section(self, catalog: ExhibitCatalog) -> str:
        lines: list[str] = []
        if catalog.booth.name:
            lines.append(f"Booth: {catalog.booth.name}")
        if catalog.booth.description:
            lines.append(f"Booth description: {catalog.booth.description}")
        if catalog.companion.name:
            lines.append(f"Companion name: {catalog.companion.name}")
        if catalog.companion.role:
            lines.append(f"Companion role: {catalog.companion.role}")
        return "\n".join(lines)

    def _build_memory_section(self, memories: list[CharacterMemoryItem]) -> str:
        if not memories:
            return ""

        lines = ["Relevant character memories:"]
        for memory in memories:
            lines.append(f"- {memory.title} ({memory.id}): {memory.summary}")
            if memory.details:
                lines.append(f"  Details: {memory.details}")
        return "\n".join(lines)

    def _build_exhibit_section(self, catalog: ExhibitCatalog) -> str:
        if not catalog.exhibits:
            return ""

        lines = ["Exhibits:"]
        for exhibit in catalog.exhibits:
            lines.append(f"- {exhibit.title} ({exhibit.id}): {exhibit.summary}")
            if exhibit.details:
                lines.append(f"  Details: {exhibit.details}")
            if exhibit.links:
                lines.append(f"  Links: {', '.join(exhibit.links)}")
        return "\n".join(lines)


class KeywordCatalogSelector:
    def select(
        self,
        request: ChatCompletionRequest,
        catalogs: list[ExhibitCatalog],
    ) -> ExhibitCatalog | None:
        if not catalogs:
            return None

        best_catalog = catalogs[0]
        best_score = -1
        for catalog in catalogs:
            score = self.score(request, catalog)
            if score > best_score:
                best_catalog = catalog
                best_score = score
        return best_catalog

    def score(self, request: ChatCompletionRequest, catalog: ExhibitCatalog) -> int:
        user_texts = [
            self._message_content_text(message)
            for message in request.messages
            if message.role == "user"
        ]
        user_texts = [text for text in user_texts if text]
        if not user_texts:
            return 0

        searchable_text = self._catalog_searchable_text(catalog)
        all_user_text = " ".join(user_texts).lower()
        latest_user_text = user_texts[-1].lower()
        return self._score_text(all_user_text, searchable_text) + self._score_text(
            latest_user_text,
            searchable_text,
        )

    def _score_text(self, user_text: str, searchable_text: str) -> int:
        score = 0
        for token in self._tokens(user_text):
            if token in searchable_text:
                score += 1
        return score

    def _catalog_searchable_text(self, catalog: ExhibitCatalog) -> str:
        parts = [
            catalog.id,
            *catalog.keywords,
            catalog.booth.name,
            catalog.booth.description,
            catalog.companion.name,
            catalog.companion.role,
        ]
        for exhibit in catalog.exhibits:
            parts.extend(
                [
                    exhibit.id,
                    exhibit.title,
                    exhibit.summary,
                    exhibit.details,
                    *exhibit.keywords,
                ]
            )
        return " ".join(part.lower() for part in parts if part)

    def _message_content_text(self, message: ChatMessage) -> str:
        if isinstance(message.content, str):
            return message.content
        if isinstance(message.content, list):
            text_parts: list[str] = []
            for part in message.content:
                text = part.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
            return " ".join(text_parts)
        return ""

    def _tokens(self, text: str) -> list[str]:
        return [
            token for token in TOKEN_PATTERN.findall(text.lower()) if len(token) >= 2
        ]


class KeywordMemorySelector:
    def __init__(self, max_items: int = 3) -> None:
        self._max_items = max_items

    def select(
        self,
        request: ChatCompletionRequest,
        catalogs: list[CharacterMemoryCatalog],
    ) -> list[CharacterMemoryItem]:
        if not catalogs:
            return []

        user_text = self._request_user_text(request)
        if not user_text:
            return []

        scored: list[tuple[int, int, CharacterMemoryItem]] = []
        position = 0
        for catalog in catalogs:
            catalog_keywords = [catalog.id, *catalog.keywords]
            for memory in catalog.memories:
                score = self._score_memory(user_text, catalog_keywords, memory)
                if score > 0:
                    scored.append((score, position, memory))
                position += 1

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [memory for _, _, memory in scored[: self._max_items]]

    def _request_user_text(self, request: ChatCompletionRequest) -> str:
        texts = [
            self._message_content_text(message)
            for message in request.messages
            if message.role == "user"
        ]
        return " ".join(text for text in texts if text).lower()

    def _score_memory(
        self,
        user_text: str,
        catalog_keywords: list[str],
        memory: CharacterMemoryItem,
    ) -> int:
        searchable_text = self._memory_searchable_text(catalog_keywords, memory)
        score = 0
        for token in self._tokens(user_text):
            if token in searchable_text:
                score += 1
        for keyword in [*catalog_keywords, *memory.keywords]:
            keyword_text = keyword.lower().strip()
            if keyword_text and keyword_text in user_text:
                score += 2
        return score

    def _memory_searchable_text(
        self,
        catalog_keywords: list[str],
        memory: CharacterMemoryItem,
    ) -> str:
        parts = [
            memory.id,
            memory.title,
            memory.summary,
            memory.details,
            *catalog_keywords,
            *memory.keywords,
        ]
        return " ".join(part.lower() for part in parts if part)

    def _message_content_text(self, message: ChatMessage) -> str:
        if isinstance(message.content, str):
            return message.content
        if isinstance(message.content, list):
            text_parts: list[str] = []
            for part in message.content:
                text = part.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
            return " ".join(text_parts)
        return ""

    def _tokens(self, text: str) -> list[str]:
        return [
            token for token in TOKEN_PATTERN.findall(text.lower()) if len(token) >= 2
        ]


class CompanionContextProvider:
    def __init__(
        self,
        persona_prompt: str,
        catalogs: list[ExhibitCatalog],
        memory_catalogs: list[CharacterMemoryCatalog] | None = None,
        *,
        selector: KeywordCatalogSelector | None = None,
        memory_selector: KeywordMemorySelector | None = None,
        builder: CompanionContextBuilder | None = None,
    ) -> None:
        self._persona_prompt = persona_prompt
        self._catalogs = catalogs
        self._memory_catalogs = memory_catalogs or []
        self._selector = selector or KeywordCatalogSelector()
        self._memory_selector = memory_selector or KeywordMemorySelector()
        self._builder = builder or CompanionContextBuilder()

    def build_for_request(self, request: ChatCompletionRequest) -> str:
        catalog = self._selector.select(request, self._catalogs)
        if catalog is None:
            return ""
        memories = self._memory_selector.select(request, self._memory_catalogs)
        return self._builder.build(self._persona_prompt, catalog, memories)
