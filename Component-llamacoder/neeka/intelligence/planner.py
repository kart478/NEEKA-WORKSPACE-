from pydantic import BaseModel, Field

from .exceptions import InvalidAIResponseError
from .providers.base import AIProvider


class PlanStep(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""


class WorkPlan(BaseModel):
    goal: str = Field(min_length=1)
    project_id: str | None = None
    steps: list[PlanStep] = Field(min_length=1)


class Planner:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    def plan(self, goal: str, context: dict) -> WorkPlan:
        response = self.provider.plan(goal, context)
        try:
            return WorkPlan.model_validate({"goal": goal, **response.data})
        except Exception as error:
            raise InvalidAIResponseError(f"Provider returned an invalid plan: {error}") from error