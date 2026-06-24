from __future__ import annotations

from app.config.settings import (
    DEFAULT_COMPANION_PROMPT_PATH,
    DEFAULT_EXHIBIT_CATALOG_PATH,
    DEFAULT_INJECTION_GUARD_DB_PATH,
    DEFAULT_INJECTION_GUARD_MASK_TEXT,
    DEFAULT_INJECTION_GUARD_MAX_ENTRIES,
    DEFAULT_INJECTION_GUARD_MIN_PROMPT_CHARS,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    AppConfig,
)


def test_endpoint_config_normalizes_api_base_and_defaults_timeout() -> None:
    config = AppConfig.model_validate(
        {
            "router": {
                "api_base": "http://127.0.0.1:1234/v1/",
                "model": "router-model",
            },
            "actor": {
                "api_base": "http://127.0.0.1:1234/v1",
                "model": "actor-model",
            },
            "formatter": {
                "api_base": "http://127.0.0.1:1234/v1",
                "model": "formatter-model",
            },
            "director": {
                "api_base": "http://127.0.0.1:1234/v1",
                "model": "director-model",
            },
        }
    )

    assert config.router.api_base == "http://127.0.0.1:1234/v1"
    assert config.router.request_timeout_seconds == DEFAULT_REQUEST_TIMEOUT_SECONDS
    assert config.actor.extra_body == {}
    assert config.workflow.router_enabled is True
    assert config.workflow.router_prompt_path == "app/prompts/router_decision.md"
    assert config.workflow.director_prompt_path == "app/prompts/director.md"
    assert config.workflow.formatter_prompt_path == "app/prompts/formatter.md"
    assert config.workflow.router_debug_logging is False
    assert config.workflow.formatter_enabled is False
    assert config.workflow.router_max_tokens == 128
    assert config.workflow.router_temperature == 0.0
    assert config.companion.enabled is False
    assert config.companion.persona_prompt_path == DEFAULT_COMPANION_PROMPT_PATH
    assert config.companion.exhibit_catalog_path == DEFAULT_EXHIBIT_CATALOG_PATH
    assert config.companion.exhibit_catalog_paths == []
    assert config.companion.effective_exhibit_catalog_paths() == [
        DEFAULT_EXHIBIT_CATALOG_PATH
    ]
    assert config.injection_guard.enabled is False
    assert config.injection_guard.db_path == DEFAULT_INJECTION_GUARD_DB_PATH
    assert config.injection_guard.max_entries == DEFAULT_INJECTION_GUARD_MAX_ENTRIES
    assert (
        config.injection_guard.min_prompt_chars
        == DEFAULT_INJECTION_GUARD_MIN_PROMPT_CHARS
    )
    assert config.injection_guard.mask_text == DEFAULT_INJECTION_GUARD_MASK_TEXT
    assert config.injection_guard.fallback_messages


def test_endpoint_config_accepts_extra_body_companion_and_injection_guard_config() -> None:
    config = AppConfig.model_validate(
        {
            "router": {
                "api_base": "http://127.0.0.1:1234/v1",
                "model": "router-model",
            },
            "actor": {
                "api_base": "http://127.0.0.1:1234/v1",
                "model": "actor-model",
                "extra_body": {
                    "reasoning_effort": "low",
                },
            },
            "formatter": {
                "api_base": "http://127.0.0.1:1234/v1",
                "model": "formatter-model",
            },
            "director": {
                "api_base": "http://127.0.0.1:1234/v1",
                "model": "director-model",
                "extra_body": {
                    "reasoning_effort": "low",
                },
            },
            "companion": {
                "enabled": True,
                "persona_prompt_path": "app/prompts/companion.md",
                "exhibit_catalog_path": "app/exhibits/catalog.example.yaml",
                "exhibit_catalog_paths": [
                    "app/exhibits/catalog.gateway.yaml",
                    "app/exhibits/catalog.creative.example.yaml",
                ],
            },
            "injection_guard": {
                "enabled": True,
                "db_path": "tmp/injection.sqlite3",
                "max_entries": 123,
                "min_prompt_chars": 20,
                "mask_text": "[removed]",
                "fallback_messages": ["try again"],
            },
        }
    )

    assert config.actor.extra_body == {
        "reasoning_effort": "low",
    }
    assert config.director.extra_body == {
        "reasoning_effort": "low",
    }
    assert config.companion.enabled is True
    assert config.companion.effective_exhibit_catalog_paths() == [
        "app/exhibits/catalog.gateway.yaml",
        "app/exhibits/catalog.creative.example.yaml",
    ]
    assert config.injection_guard.enabled is True
    assert config.injection_guard.db_path == "tmp/injection.sqlite3"
    assert config.injection_guard.max_entries == 123
    assert config.injection_guard.min_prompt_chars == 20
    assert config.injection_guard.mask_text == "[removed]"
    assert config.injection_guard.fallback_messages == ["try again"]
