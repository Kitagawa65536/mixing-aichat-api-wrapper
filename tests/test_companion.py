from __future__ import annotations

from app.companion import (
    CompanionContextBuilder,
    ExhibitCatalog,
    ExhibitCatalogLoader,
    KeywordCatalogSelector,
)
from app.models.chat import ChatCompletionRequest, ChatMessage


def test_exhibit_catalog_loader_reads_yaml(tmp_path) -> None:
    catalog_path = tmp_path / "catalog.yaml"
    catalog_path.write_text(
        """
id: test-catalog
keywords:
  - test
booth:
  name: Test Booth
  description: Test booth description.
companion:
  name: Test Guide
  role: Booth companion
exhibits:
  - id: work-1
    title: Work One
    summary: First exhibit.
    details: Detailed notes.
    keywords:
      - first
    links:
      - https://example.com/work-1
""".strip(),
        encoding="utf-8",
    )

    catalog = ExhibitCatalogLoader().load(str(catalog_path))

    assert catalog.booth.name == "Test Booth"
    assert catalog.id == "test-catalog"
    assert catalog.keywords == ["test"]
    assert catalog.companion.name == "Test Guide"
    assert catalog.exhibits[0].id == "work-1"
    assert catalog.exhibits[0].keywords == ["first"]


def test_exhibit_catalog_loader_reads_many_yaml_files(tmp_path) -> None:
    first_path = tmp_path / "first.yaml"
    second_path = tmp_path / "second.yaml"
    first_path.write_text("id: first\nbooth:\n  name: First\n", encoding="utf-8")
    second_path.write_text("id: second\nbooth:\n  name: Second\n", encoding="utf-8")

    catalogs = ExhibitCatalogLoader().load_many([str(first_path), str(second_path)])

    assert [catalog.id for catalog in catalogs] == ["first", "second"]


def test_companion_context_builder_combines_persona_and_catalog() -> None:
    catalog = ExhibitCatalog.model_validate(
        {
            "booth": {"name": "Test Booth", "description": "A demo booth."},
            "companion": {"name": "Guide", "role": "Explains exhibits."},
            "exhibits": [
                {
                    "id": "work-1",
                    "title": "Work One",
                    "summary": "First exhibit.",
                    "details": "Detailed notes.",
                    "links": ["https://example.com/work-1"],
                }
            ],
        }
    )

    context = CompanionContextBuilder().build("Persona text.", catalog)

    assert "Persona text." in context
    assert "Booth: Test Booth" in context
    assert "Companion name: Guide" in context
    assert "Work One (work-1): First exhibit." in context


def test_keyword_catalog_selector_picks_matching_catalog() -> None:
    selector = KeywordCatalogSelector()
    gateway_catalog = ExhibitCatalog.model_validate(
        {
            "id": "gateway",
            "keywords": ["gateway", "router"],
            "booth": {"name": "Gateway Booth"},
        }
    )
    creative_catalog = ExhibitCatalog.model_validate(
        {
            "id": "creative",
            "keywords": ["visual", "prototype"],
            "booth": {"name": "Creative Booth"},
        }
    )
    request = ChatCompletionRequest(
        model="gateway-model",
        messages=[ChatMessage(role="user", content="router workflowを見たいです")],
    )

    selected = selector.select(request, [creative_catalog, gateway_catalog])

    assert selected == gateway_catalog


def test_keyword_catalog_selector_falls_back_to_first_catalog() -> None:
    selector = KeywordCatalogSelector()
    first_catalog = ExhibitCatalog.model_validate({"id": "first"})
    second_catalog = ExhibitCatalog.model_validate({"id": "second"})
    request = ChatCompletionRequest(
        model="gateway-model",
        messages=[ChatMessage(role="user", content="天気の話をして")],
    )

    selected = selector.select(request, [first_catalog, second_catalog])

    assert selected == first_catalog


def test_keyword_catalog_selector_prioritizes_latest_user_message() -> None:
    selector = KeywordCatalogSelector()
    gateway_catalog = ExhibitCatalog.model_validate(
        {"id": "gateway", "keywords": ["gateway"]}
    )
    creative_catalog = ExhibitCatalog.model_validate(
        {"id": "creative", "keywords": ["creative"]}
    )
    request = ChatCompletionRequest(
        model="gateway-model",
        messages=[
            ChatMessage(role="user", content="gatewayの説明を聞きたい"),
            ChatMessage(role="assistant", content="案内します"),
            ChatMessage(role="user", content="やっぱりcreative demoを教えて"),
        ],
    )

    selected = selector.select(request, [gateway_catalog, creative_catalog])

    assert selected == creative_catalog
