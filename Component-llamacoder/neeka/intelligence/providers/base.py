from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderResponse:
    content: str
    data: dict[str, Any] = field(default_factory=dict)


class BaseAIProvider(ABC):
    provider_name: str

    @abstractmethod
    def generate(self, prompt: str, context: dict[str, Any]) -> ProviderResponse:
        raise NotImplementedError

    @abstractmethod
    def analyze(self, context: dict[str, Any]) -> ProviderResponse:
        raise NotImplementedError

    @abstractmethod
    def plan(self, goal: str, context: dict[str, Any]) -> ProviderResponse:
        raise NotImplementedError


class AIProvider(Protocol):
    provider_name: str

    def generate(self, prompt: str, context: dict[str, Any]) -> ProviderResponse: ...
    def analyze(self, context: dict[str, Any]) -> ProviderResponse: ...
    def plan(self, goal: str, context: dict[str, Any]) -> ProviderResponse: ...