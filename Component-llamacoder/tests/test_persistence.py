import sqlite3

import pytest

from neeka import NEEKAEngine
from neeka.brain.exceptions import (
    CircularDependencyError,
    DuplicateMemberError,
    InvalidProjectMembershipError,
    ProjectNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from neeka.brain.task import TaskStatus
from neeka.brain.user import UserRole
from neeka.persistence.backup import backup_database
from neeka.persistence.database import Database


def make_engine(tmp_path):
    return NEEKAEngine(tmp_path / "neeka.db")


def make_project(engine):
    owner = engine.create_user("Owner", "owner@example.com", UserRole.MANAGER)
    member = engine.create_user("Member", "member@example.com")
    project = engine.create_project("Project", "Description", owner.id)
    engine.add_project_member(project.id, member.id, owner.id)
    return owner, member, project


def test_user_project_and_membership_round_trip(tmp_path):
    engine = make_engine(tmp_path)
    owner, member, project = make_project(engine)

    restarted = make_engine(tmp_path)
    assert restarted.get_user(owner.id).email == owner.email
    assert restarted.get_project(project.id).member_ids == [owner.id, member.id]


def test_duplicate_membership_and_invalid_references(tmp_path):
    engine = make_engine(tmp_path)
    owner, member, project = make_project(engine)
    with pytest.raises(DuplicateMemberError):
        engine.add_project_member(project.id, member.id, owner.id)
    with pytest.raises(UserNotFoundError):
        engine.create_project("Invalid", "", "missing")
    with pytest.raises(ProjectNotFoundError):
        engine.get_project("missing")
    with pytest.raises(TaskNotFoundError):
        engine.get_task("missing")


def test_task_assignment_and_state_persist_after_restart(tmp_path):
    engine = make_engine(tmp_path)
    owner, member, project = make_project(engine)
    task = engine.create_task("Collect Data", "", project.id, owner.id)
    engine.assign_task(task.id, member.id, owner.id)
    engine.start_task(task.id, member.id)
    engine.complete_task(task.id, member.id)

    restarted = make_engine(tmp_path)
    persisted = restarted.get_task(task.id)
    assert persisted.assigned_to == member.id
    assert persisted.status == TaskStatus.COMPLETED
    assert persisted.started_at is not None
    assert persisted.completed_at is not None


def test_invalid_assignment_requires_project_membership(tmp_path):
    engine = make_engine(tmp_path)
    owner = engine.create_user("Owner", "owner@example.com")
    outsider = engine.create_user("Outsider", "outsider@example.com")
    project = engine.create_project("Project", "", owner.id)
    task = engine.create_task("Task", "", project.id, owner.id)
    with pytest.raises(InvalidProjectMembershipError):
        engine.assign_task(task.id, outsider.id, owner.id)


def test_dependencies_and_cycle_protection(tmp_path):
    engine = make_engine(tmp_path)
    owner, _, project = make_project(engine)
    task_a = engine.create_task("A", "", project.id, owner.id)
    task_b = engine.create_task("B", "", project.id, owner.id)
    task_c = engine.create_task("C", "", project.id, owner.id)
    engine.add_task_dependency(task_b.id, task_a.id, owner.id)
    engine.add_task_dependency(task_c.id, task_b.id, owner.id)
    with pytest.raises(CircularDependencyError):
        engine.add_task_dependency(task_a.id, task_c.id, owner.id)

    restarted = make_engine(tmp_path)
    assert restarted.get_task(task_c.id).dependency_ids == [task_b.id]


def test_completion_reacts_and_unlocks_next_task(tmp_path):
    engine = make_engine(tmp_path)
    owner = engine.create_user("Owner", "owner@example.com", UserRole.MANAGER)
    john = engine.create_user("John", "john@example.com")
    sarah = engine.create_user("Sarah", "sarah@example.com")
    project = engine.create_project("Project", "", owner.id)
    engine.add_project_member(project.id, john.id, owner.id)
    engine.add_project_member(project.id, sarah.id, owner.id)

    task_a = engine.create_task("Task A", "", project.id, owner.id)
    task_b = engine.create_task("Task B", "", project.id, owner.id)
    engine.add_task_dependency(task_b.id, task_a.id, owner.id)
    engine.assign_task(task_a.id, john.id, owner.id)
    engine.start_task(task_a.id, john.id)
    engine.complete_task(task_a.id, john.id)

    assert engine.get_task(task_b.id).status == TaskStatus.READY
    event_types = [event.event_type.value for event in engine.get_events()]
    assert event_types.index("TASK_COMPLETED") < event_types.index("TASK_READY")

    engine.assign_task(task_b.id, sarah.id, owner.id)
    assert engine.get_task(task_b.id).assigned_to == sarah.id


def test_event_history_persists(tmp_path):
    engine = make_engine(tmp_path)
    owner, member, project = make_project(engine)
    task = engine.create_task("Task", "", project.id, owner.id)
    engine.assign_task(task.id, member.id, owner.id)
    event_types = {event.event_type.value for event in make_engine(tmp_path).get_events()}
    assert {"PROJECT_CREATED", "USER_ADDED_TO_PROJECT", "TASK_CREATED", "TASK_ASSIGNED"} <= event_types


def test_transaction_rolls_back_on_failure(tmp_path):
    database = Database(tmp_path / "rollback.db")
    with pytest.raises(RuntimeError):
        with database.session() as connection:
            connection.execute(
                "INSERT INTO users(id, name, email, role, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("u1", "User", "user@example.com", "MEMBER", 1, "now", "now"),
            )
            raise RuntimeError("abort")
    with database.session() as connection:
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_foreign_keys_are_enforced(tmp_path):
    database = Database(tmp_path / "foreign-keys.db")
    with pytest.raises(sqlite3.IntegrityError):
        with database.session() as connection:
            connection.execute(
                "INSERT INTO projects(id, name, description, owner_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("p1", "Project", "", "missing", "PLANNED", "now", "now"),
            )


def test_backup_contains_persistent_data(tmp_path):
    engine = make_engine(tmp_path)
    owner = engine.create_user("Owner", "owner@example.com")
    backup_path = backup_database(tmp_path / "neeka.db", tmp_path / "backup" / "neeka.db")
    backup_engine = NEEKAEngine(backup_path)
    assert backup_engine.get_user(owner.id).name == "Owner"


def test_complete_restart_scenario(tmp_path):
    first = make_engine(tmp_path)
    owner, member, project = make_project(first)
    collect = first.create_task("Collect Data", "", project.id, owner.id)
    write = first.create_task("Write Report", "", project.id, owner.id)
    first.add_task_dependency(write.id, collect.id, owner.id)
    first.assign_task(collect.id, member.id, owner.id)
    first.start_task(collect.id, member.id)
    first.complete_task(collect.id, member.id)
    first.close()

    second = make_engine(tmp_path)
    assert second.get_project(project.id).name == "Project"
    assert {task.title for task in second.get_project_tasks(project.id)} == {"Collect Data", "Write Report"}
    assert second.get_task(write.id).dependency_ids == [collect.id]
    assert second.get_task(collect.id).assigned_to == member.id
    assert second.get_task(collect.id).status == TaskStatus.COMPLETED
    assert len(second.get_events()) >= 7