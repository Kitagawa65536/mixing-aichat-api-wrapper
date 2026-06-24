from __future__ import annotations

from app.config.settings import EndpointConfig
from app.llm.openai_compatible import OpenAICompatibleClient


class RouterClient(OpenAICompatibleClient):
    def __init__(self, endpoint: EndpointConfig) -> None:
        super().__init__("router", endpoint)


class ActorClient(OpenAICompatibleClient):
    def __init__(self, endpoint: EndpointConfig) -> None:
        super().__init__("actor", endpoint)


class DirectorClient(OpenAICompatibleClient):
    def __init__(self, endpoint: EndpointConfig) -> None:
        super().__init__("director", endpoint)


class FormatterClient(OpenAICompatibleClient):
    def __init__(self, endpoint: EndpointConfig) -> None:
        super().__init__("formatter", endpoint)
