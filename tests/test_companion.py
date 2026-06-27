from __future__ import annotations

from app.companion import (
    CharacterMemoryLoader,
    CompanionContextBuilder,
    CompanionContextProvider,
    ExhibitCatalog,
    ExhibitCatalogLoader,
    KeywordCatalogSelector,
    KeywordMemorySelector,
)
from app.companion.memory import CharacterMemoryCatalog
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


def test_character_memory_loader_reads_yaml(tmp_path) -> None:
    memory_path = tmp_path / "memory.yaml"
    memory_path.write_text(
        """
id: test-memories
keywords:
  - childhood
memories:
  - id: quail-egg
    title: Quail egg memory
    summary: Thought quail eggs were tiny chicken eggs.
    details: Later learned quails are different birds.
    keywords:
      - quail egg
""".strip(),
        encoding="utf-8",
    )

    memory_catalog = CharacterMemoryLoader().load(str(memory_path))

    assert memory_catalog.id == "test-memories"
    assert memory_catalog.keywords == ["childhood"]
    assert memory_catalog.memories[0].id == "quail-egg"
    assert memory_catalog.memories[0].keywords == ["quail egg"]


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


def test_companion_context_builder_includes_related_memories() -> None:
    catalog = ExhibitCatalog.model_validate({"id": "test"})
    memory_catalog = CharacterMemoryCatalog.model_validate(
        {
            "memories": [
                {
                    "id": "quail-egg",
                    "title": "Quail egg memory",
                    "summary": "Thought quail eggs were tiny chicken eggs.",
                    "details": "Later learned quails are different birds.",
                }
            ]
        }
    )

    context = CompanionContextBuilder().build(
        "Persona text.",
        catalog,
        memory_catalog.memories,
    )

    assert "Relevant character memories:" in context
    assert "Quail egg memory (quail-egg)" in context
    assert "Later learned quails are different birds." in context


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


def test_keyword_memory_selector_picks_matching_memories() -> None:
    selector = KeywordMemorySelector()
    memory_catalog = CharacterMemoryCatalog.model_validate(
        {
            "memories": [
                {
                    "id": "quail-egg",
                    "title": "子供の頃のうずらの卵の勘違い",
                    "summary": "うずらの卵は小さい鶏の卵だと思っていた。",
                    "keywords": ["うずらの卵", "ウズラ", "ニワトリ"],
                },
                {
                    "id": "rain",
                    "title": "Rain memory",
                    "summary": "Liked walking in the rain.",
                    "keywords": ["rain"],
                },
            ]
        }
    )
    request = ChatCompletionRequest(
        model="gateway-model",
        messages=[
            ChatMessage(role="user", content="うずらの卵について思い出ある？"),
        ],
    )

    selected = selector.select(request, [memory_catalog])

    assert [memory.id for memory in selected] == ["quail-egg"]


def test_keyword_memory_selector_omits_unrelated_memories() -> None:
    selector = KeywordMemorySelector()
    memory_catalog = CharacterMemoryCatalog.model_validate(
        {
            "memories": [
                {
                    "id": "quail-egg",
                    "title": "子供の頃のうずらの卵の勘違い",
                    "summary": "うずらの卵は小さい鶏の卵だと思っていた。",
                    "keywords": ["うずらの卵", "ウズラ", "ニワトリ"],
                }
            ]
        }
    )
    request = ChatCompletionRequest(
        model="gateway-model",
        messages=[ChatMessage(role="user", content="展示の構成を教えて")],
    )

    selected = selector.select(request, [memory_catalog])

    assert selected == []


def test_companion_context_provider_adds_matching_memory_to_context() -> None:
    provider = CompanionContextProvider(
        "Persona text.",
        [ExhibitCatalog.model_validate({"id": "test"})],
        [
            CharacterMemoryCatalog.model_validate(
                {
                    "memories": [
                        {
                            "id": "quail-egg",
                            "title": "子供の頃のうずらの卵の勘違い",
                            "summary": (
                                "子供の時、うずらの卵はニワトリが時々すごく"
                                "小さい卵を生むのだと思っていた。"
                            ),
                            "details": (
                                "ウズラという鳥がいると知った時に、鶏の卵とは"
                                "別物なのだと初めて知った。"
                            ),
                            "keywords": ["うずらの卵", "ウズラ", "ニワトリ"],
                        }
                    ]
                }
            )
        ],
    )
    request = ChatCompletionRequest(
        model="gateway-model",
        messages=[ChatMessage(role="user", content="うずらの卵の話を覚えてる？")],
    )

    context = provider.build_for_request(request)

    assert "Persona text." in context
    assert "Relevant character memories:" in context
    assert "子供の時、うずらの卵はニワトリ" in context
