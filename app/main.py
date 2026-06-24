from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.companion import CompanionContextProvider, ExhibitCatalogLoader
from app.api.models import router as models_router
from app.config.settings import AppConfig, load_config
from app.llm.roles import ActorClient, DirectorClient, FormatterClient, RouterClient
from app.prompts.loader import PromptLoader
from app.storage.events import NoopConversationEventSink
from app.storage.injection_guard import InjectionPromptStore
from app.workflow.orchestrator import Orchestrator


def create_app(config: AppConfig | None = None) -> FastAPI:
    app_config = config or load_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await app.state.router_client.aclose()
        await app.state.actor_client.aclose()
        await app.state.director_client.aclose()
        await app.state.formatter_client.aclose()

    app = FastAPI(title="Local Roleplay LLM Gateway", lifespan=lifespan)

    app.state.config = app_config
    app.state.router_client = RouterClient(app_config.router)
    app.state.actor_client = ActorClient(app_config.actor)
    app.state.director_client = DirectorClient(app_config.director)
    app.state.formatter_client = FormatterClient(app_config.formatter)
    app.state.prompt_loader = PromptLoader()
    app.state.router_prompt = (
        app.state.prompt_loader.load(app_config.workflow.router_prompt_path)
        if app_config.workflow.router_enabled
        else ""
    )
    app.state.director_prompt = app.state.prompt_loader.load(
        app_config.workflow.director_prompt_path
    )
    app.state.formatter_prompt = (
        app.state.prompt_loader.load(app_config.workflow.formatter_prompt_path)
        if app_config.workflow.formatter_enabled
        else ""
    )
    app.state.companion_context_provider = None
    if app_config.companion.enabled:
        persona_prompt = app.state.prompt_loader.load(
            app_config.companion.persona_prompt_path
        )
        exhibit_catalogs = ExhibitCatalogLoader().load_many(
            app_config.companion.effective_exhibit_catalog_paths()
        )
        app.state.companion_context_provider = CompanionContextProvider(
            persona_prompt,
            exhibit_catalogs,
        )
    app.state.event_sink = NoopConversationEventSink()
    app.state.injection_prompt_store = None
    if app_config.injection_guard.enabled:
        app.state.injection_prompt_store = InjectionPromptStore(
            app_config.injection_guard.db_path,
            max_entries=app_config.injection_guard.max_entries,
            min_prompt_chars=app_config.injection_guard.min_prompt_chars,
            mask_text=app_config.injection_guard.mask_text,
        )
    app.state.orchestrator = Orchestrator(
        actor_client=app.state.actor_client,
        router_client=app.state.router_client,
        director_client=app.state.director_client,
        formatter_client=app.state.formatter_client,
        workflow_config=app_config.workflow,
        router_prompt=app.state.router_prompt,
        director_prompt=app.state.director_prompt,
        formatter_prompt=app.state.formatter_prompt,
        companion_context_provider=app.state.companion_context_provider,
        event_sink=app.state.event_sink,
        injection_prompt_store=app.state.injection_prompt_store,
        injection_fallback_messages=app_config.injection_guard.fallback_messages,
    )

    app.include_router(chat_router)
    app.include_router(models_router)
    return app


app = create_app()
