from fastapi import APIRouter, Depends, Query, status

from neeka.brain.engine import NEEKAEngine
from neeka.brain.event import Event
from neeka.brain.exceptions import AutomationExecutionNotFoundError, WorkflowNotFoundError
from neeka.brain.project import Project
from neeka.brain.task import Task
from neeka.brain.user import User
from neeka.services.control import ControlService
from neeka.workflow.definitions import STANDARD_TASK_WORKFLOW
from .dependencies import get_engine, get_service
from .schemas import (
    ActorRequest, AssignmentRequest, DependencyRequest, EventOut, ExecutionOut,
    MemberRequest, ProjectCreate, ProjectOut, ProjectUpdate, TaskCreate, TaskOut, TaskUpdate,
    UserCreate, UserOut, UserUpdate, WorkflowOut,
)

router = APIRouter()


def event_out(event: Event) -> EventOut:
    return EventOut(event_id=event.id, event_type=event.event_type.value, timestamp=event.timestamp,
                    actor_id=event.actor_id, entity_id=event.source_entity, metadata=event.metadata)


def workflow_out() -> WorkflowOut:
    definition = STANDARD_TASK_WORKFLOW
    return WorkflowOut(
        workflow_id=definition.workflow_id, name=definition.name, description=definition.description,
        version=definition.version, active=definition.active,
        states=sorted(state.value for state in definition.state_machine.states),
        transitions=sorted(
            [{"source": item.source.value, "destination": item.destination.value, "trigger": item.trigger}
             for item in definition.state_machine.transitions],
            key=lambda item: (item["source"], item["destination"]),
        ),
    )


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, service: ControlService = Depends(get_service)) -> User:
    return service.create_user(payload.name, payload.email, payload.role)


@router.get("/users", response_model=list[UserOut])
def list_users(engine: NEEKAEngine = Depends(get_engine)) -> list[User]:
    return engine.list_users()


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: str, engine: NEEKAEngine = Depends(get_engine)) -> User:
    return engine.get_user(user_id)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: UserUpdate, service: ControlService = Depends(get_service)) -> User:
    return service.update_user(user_id, **payload.model_dump(exclude_unset=True))


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, service: ControlService = Depends(get_service)) -> Project:
    return service.create_project(payload.name, payload.description, payload.owner_id)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(engine: NEEKAEngine = Depends(get_engine)) -> list[Project]:
    return engine.list_projects()


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, engine: NEEKAEngine = Depends(get_engine)) -> Project:
    return engine.get_project(project_id)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, payload: ProjectUpdate, engine: NEEKAEngine = Depends(get_engine)) -> Project:
    return engine.update_project(project_id, **payload.model_dump(exclude_unset=True))


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, actor_id: str = Query(...), engine: NEEKAEngine = Depends(get_engine)) -> None:
    engine.delete_project(project_id, actor_id)


@router.post("/projects/{project_id}/members", status_code=status.HTTP_204_NO_CONTENT)
def add_member(project_id: str, payload: MemberRequest, engine: NEEKAEngine = Depends(get_engine)) -> None:
    engine.add_project_member(project_id, payload.user_id, payload.actor_id)


@router.delete("/projects/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(project_id: str, user_id: str, actor_id: str = Query(...), engine: NEEKAEngine = Depends(get_engine)) -> None:
    engine.remove_project_member(project_id, user_id, actor_id)


@router.get("/projects/{project_id}/members", response_model=list[UserOut])
def list_members(project_id: str, engine: NEEKAEngine = Depends(get_engine)) -> list[User]:
    project = engine.get_project(project_id)
    return [engine.get_user(user_id) for user_id in project.member_ids]


@router.post("/projects/{project_id}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(project_id: str, payload: TaskCreate, service: ControlService = Depends(get_service)) -> Task:
    return service.create_task(project_id, payload.title, payload.description, payload.creator_id, payload.priority)


@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
def list_project_tasks(project_id: str, engine: NEEKAEngine = Depends(get_engine)) -> list[Task]:
    engine.get_project(project_id)
    return engine.list_tasks(project_id)


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: str, engine: NEEKAEngine = Depends(get_engine)) -> Task:
    return engine.get_task(task_id)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: str, payload: TaskUpdate, service: ControlService = Depends(get_service)) -> Task:
    return service.update_task(task_id, **payload.model_dump(exclude_unset=True))


@router.post("/tasks/{task_id}/assign", response_model=TaskOut)
def assign_task(task_id: str, payload: AssignmentRequest, engine: NEEKAEngine = Depends(get_engine)) -> Task:
    engine.assign_task(task_id, payload.user_id, payload.actor_id)
    return engine.get_task(task_id)


@router.post("/tasks/{task_id}/start", response_model=TaskOut)
def start_task(task_id: str, payload: ActorRequest, engine: NEEKAEngine = Depends(get_engine)) -> Task:
    engine.start_task(task_id, payload.actor_id)
    return engine.get_task(task_id)


@router.post("/tasks/{task_id}/complete", response_model=TaskOut)
def complete_task(task_id: str, payload: ActorRequest, engine: NEEKAEngine = Depends(get_engine)) -> Task:
    engine.complete_task(task_id, payload.actor_id)
    return engine.get_task(task_id)


@router.post("/tasks/{task_id}/block", response_model=TaskOut)
def block_task(task_id: str, payload: ActorRequest, engine: NEEKAEngine = Depends(get_engine)) -> Task:
    engine.block_task(task_id, payload.actor_id)
    return engine.get_task(task_id)


@router.post("/tasks/{task_id}/cancel", response_model=TaskOut)
def cancel_task(task_id: str, payload: ActorRequest, engine: NEEKAEngine = Depends(get_engine)) -> Task:
    engine.cancel_task(task_id, payload.actor_id)
    return engine.get_task(task_id)


@router.post("/tasks/{task_id}/dependencies", status_code=status.HTTP_204_NO_CONTENT)
def add_dependency(task_id: str, payload: DependencyRequest, engine: NEEKAEngine = Depends(get_engine)) -> None:
    engine.add_task_dependency(task_id, payload.depends_on_id, payload.actor_id)


@router.get("/tasks/{task_id}/dependencies", response_model=list[TaskOut])
def list_dependencies(task_id: str, engine: NEEKAEngine = Depends(get_engine)) -> list[Task]:
    task = engine.get_task(task_id)
    return [engine.get_task(dependency_id) for dependency_id in task.dependency_ids]


@router.delete("/tasks/{task_id}/dependencies/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_dependency(task_id: str, dependency_id: str, actor_id: str = Query(...), engine: NEEKAEngine = Depends(get_engine)) -> None:
    engine.remove_task_dependency(task_id, dependency_id, actor_id)


@router.get("/events", response_model=list[EventOut])
def list_events(engine: NEEKAEngine = Depends(get_engine)) -> list[EventOut]:
    return [event_out(event) for event in engine.get_events()]


@router.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: str, engine: NEEKAEngine = Depends(get_engine)) -> EventOut:
    return event_out(engine.get_event(event_id))


@router.get("/projects/{project_id}/events", response_model=list[EventOut])
def project_events(project_id: str, engine: NEEKAEngine = Depends(get_engine)) -> list[EventOut]:
    project = engine.get_project(project_id)
    entity_ids = {project_id, *project.task_ids}
    return [event_out(event) for event in engine.get_events() if event.source_entity in entity_ids]


@router.get("/tasks/{task_id}/events", response_model=list[EventOut])
def task_events(task_id: str, engine: NEEKAEngine = Depends(get_engine)) -> list[EventOut]:
    engine.get_task(task_id)
    return [event_out(event) for event in engine.get_events() if event.source_entity == task_id]


@router.get("/automation/executions", response_model=list[ExecutionOut])
def executions(engine: NEEKAEngine = Depends(get_engine)) -> list[dict]:
    return engine.list_automation_executions()


@router.get("/automation/failures", response_model=list[ExecutionOut])
def failures(engine: NEEKAEngine = Depends(get_engine)) -> list[dict]:
    return [item for item in engine.list_automation_executions() if item["status"] == "FAILED"]


@router.get("/automation/executions/{execution_id}", response_model=ExecutionOut)
def execution(execution_id: str, engine: NEEKAEngine = Depends(get_engine)) -> dict:
    item = next((item for item in engine.list_automation_executions() if item["execution_id"] == execution_id), None)
    if item is None:
        raise AutomationExecutionNotFoundError(f"Automation execution {execution_id} not found")
    return item


@router.post("/automation/executions/{execution_id}/retry", response_model=ExecutionOut)
def retry_execution(execution_id: str, engine: NEEKAEngine = Depends(get_engine)) -> dict:
    return engine.retry_automation(execution_id)


@router.get("/workflows", response_model=list[WorkflowOut])
def workflows() -> list[WorkflowOut]:
    return [workflow_out()]


@router.get("/workflows/{workflow_id}", response_model=WorkflowOut)
def workflow(workflow_id: str) -> WorkflowOut:
    definition = workflow_out()
    if definition.workflow_id != workflow_id:
        raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
    return definition


@router.get("/tasks/{task_id}/workflow", response_model=WorkflowOut)
def task_workflow(task_id: str, engine: NEEKAEngine = Depends(get_engine)) -> WorkflowOut:
    engine.get_task(task_id)
    return workflow_out()