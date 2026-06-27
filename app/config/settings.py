from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


DEFAULT_CONFIG_PATH = "config.yaml"
CONFIG_PATH_ENV = "CONFIG_PATH"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 120.0
DEFAULT_ROUTER_MAX_TOKENS = 128
DEFAULT_ROUTER_TEMPERATURE = 0.0
DEFAULT_ROUTER_PROMPT_PATH = "app/prompts/router_decision.md"
DEFAULT_DIRECTOR_PROMPT_PATH = "app/prompts/director.md"
DEFAULT_FORMATTER_PROMPT_PATH = "app/prompts/formatter.md"
DEFAULT_COMPANION_PROMPT_PATH = "app/prompts/companion.md"
DEFAULT_EXHIBIT_CATALOG_PATH = "app/exhibits/catalog.example.yaml"
DEFAULT_CHARACTER_MEMORY_PATHS: list[str] = []
DEFAULT_INJECTION_GUARD_DB_PATH = "data/injection_guard.sqlite3"
DEFAULT_INJECTION_GUARD_MAX_ENTRIES = 10000
DEFAULT_INJECTION_GUARD_MIN_PROMPT_CHARS = 12
DEFAULT_INJECTION_GUARD_MASK_TEXT = "[removed]"


class EndpointConfig(BaseModel):
    api_base: str
    api_key: str | None = None
    model: str = Field(min_length=1)
    extra_body: dict[str, Any] = Field(default_factory=dict)
    request_timeout_seconds: float = Field(
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        gt=0,
    )

    @field_validator("api_base")
    @classmethod
    def normalize_api_base(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        if not cleaned:
            raise ValueError("api_base must not be empty")
        return cleaned


class WorkflowConfig(BaseModel):
    router_enabled: bool = True
    router_debug_logging: bool = False
    formatter_enabled: bool = False
    router_prompt_path: str = DEFAULT_ROUTER_PROMPT_PATH
    director_prompt_path: str = DEFAULT_DIRECTOR_PROMPT_PATH
    formatter_prompt_path: str = DEFAULT_FORMATTER_PROMPT_PATH
    router_max_tokens: int = Field(default=DEFAULT_ROUTER_MAX_TOKENS, gt=0)
    router_temperature: float = Field(default=DEFAULT_ROUTER_TEMPERATURE, ge=0)


class CompanionConfig(BaseModel):
    enabled: bool = False
    persona_prompt_path: str = DEFAULT_COMPANION_PROMPT_PATH
    exhibit_catalog_path: str = DEFAULT_EXHIBIT_CATALOG_PATH
    exhibit_catalog_paths: list[str] = Field(default_factory=list)
    character_memory_paths: list[str] = Field(default_factory=list)

    def effective_exhibit_catalog_paths(self) -> list[str]:
        if self.exhibit_catalog_paths:
            return self.exhibit_catalog_paths
        return [self.exhibit_catalog_path]


class InjectionGuardConfig(BaseModel):
    enabled: bool = False
    db_path: str = DEFAULT_INJECTION_GUARD_DB_PATH
    max_entries: int = Field(default=DEFAULT_INJECTION_GUARD_MAX_ENTRIES, gt=0)
    min_prompt_chars: int = Field(
        default=DEFAULT_INJECTION_GUARD_MIN_PROMPT_CHARS,
        ge=1,
    )
    mask_text: str = DEFAULT_INJECTION_GUARD_MASK_TEXT
    fallback_messages: list[str] = Field(
        default_factory=lambda: [
            "よくわからないのでもう一回説明してください。",
            "少し受け取り方に迷ったので、別の言い方でもう一度教えてください。",
            "その内容では案内しづらいので、展示について聞きたいことをもう一度お願いします。",
        ]
    )

    @field_validator("mask_text")
    @classmethod
    def validate_mask_text(cls, value: str) -> str:
        if not value:
            raise ValueError("mask_text must not be empty")
        return value

    @field_validator("fallback_messages")
    @classmethod
    def validate_fallback_messages(cls, value: list[str]) -> list[str]:
        cleaned = [message.strip() for message in value if message.strip()]
        if not cleaned:
            raise ValueError("fallback_messages must not be empty")
        return cleaned


class AppConfig(BaseModel):
    router: EndpointConfig
    actor: EndpointConfig
    formatter: EndpointConfig
    director: EndpointConfig
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    companion: CompanionConfig = Field(default_factory=CompanionConfig)
    injection_guard: InjectionGuardConfig = Field(default_factory=InjectionGuardConfig)


def resolve_config_path() -> Path:
    return Path(os.getenv(CONFIG_PATH_ENV, DEFAULT_CONFIG_PATH))


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path is not None else resolve_config_path()
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            "Copy config.example.yaml to config.yaml or set CONFIG_PATH."
        )

    with config_path.open("r", encoding="utf-8") as file:
        raw_config = yaml.safe_load(file) or {}

    return AppConfig.model_validate(raw_config)
