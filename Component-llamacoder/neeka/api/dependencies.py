from fastapi import Request

from neeka.brain.engine import NEEKAEngine
from neeka.services.control import ControlService


def get_engine(request: Request) -> NEEKAEngine:
    return request.app.state.engine


def get_service(request: Request) -> ControlService:
    return request.app.state.service


def get_current_actor() -> None:
    """Authentication seam; local development currently runs without auth."""
    return None