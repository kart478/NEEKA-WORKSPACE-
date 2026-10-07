from typing import Any

from .base import BaseAIProvider, ProviderResponse


class MockAIProvider(BaseAIProvider):
    """Deterministic provider for tests and local development without credentials."""

    provider_name = "mock"

    def generate(self, prompt: str, context: dict[str, Any]) -> ProviderResponse:
        return ProviderResponse(content=f"Mock response for: {prompt}", data={"context_keys": sorted(context)})

    def analyze(self, context: dict[str, Any]) -> ProviderResponse:
        blocked = [task["title"] for task in context.get("tasks", []) if task["status"] == "BLOCKED"]
        return ProviderResponse(
            content="Mock project analysis",
            data={"summary": f"Project {context.get('name', '')} has {len(context.get('tasks', []))} tasks.",
                  "blockers": blocked},
        )

    def plan(self, goal: str, context: dict[str, Any]) -> ProviderResponse:
        return ProviderResponse(
            content=f"Plan for {goal}",
            data={"goal": goal, "steps": [
                {"title": "Clarify objective", "description": goal},
                {"title": "Execute work", "description": "Complete the planned work"},
                {"title": "Review outcome", "description": "Verify the result"},
            ], "project_id": context.get("project_id")},
        )