# tests/test_engine.py
import unittest
from brain import NEEKAEngine
from brain.user import UserRole
from brain.task import TaskStatus
from brain.exceptions import (
    InactiveUserError,
    InvalidTaskTransitionError,
    TaskDependencyError,
    DuplicateMemberError,
)


class TestNEEKAEngine(unittest.TestCase):
    def setUp(self):
        self.engine = NEEKAEngine()
        self.user = self.engine.create_user("Test User", "test@neeka.io")
        self.manager = self.engine.create_user("Manager", "manager@neeka.io", UserRole.MANAGER)
        self.project = self.engine.create_project("Test Project", "Test description", self.manager.id)

    def test_create_user(self):
        user = self.engine.create_user("New User", "new@neeka.io")
        self.assertEqual(user.name, "New User")
        self.assertTrue(user.active)

    def test_create_project(self):
        project = self.engine.create_project("New Project", "Desc", self.manager.id)
        self.assertEqual(project.name, "New Project")
        self.assertEqual(project.status.value, "PLANNED")

    def test_add_member(self):
        self.engine.add_project_member(self.project.id, self.user.id, self.manager.id)
        self.assertIn(self.user.id, self.project.member_ids)

    def test_add_duplicate_member(self):
        self.engine.add_project_member(self.project.id, self.user.id, self.manager.id)
        with self.assertRaises(DuplicateMemberError):
            self.engine.add_project_member(self.project.id, self.user.id, self.manager.id)

    def test_create_task(self):
        task = self.engine.create_task("Task 1", "Description", self.project.id, self.manager.id)
        self.assertEqual(task.status, TaskStatus.TODO)
        self.assertIn(task.id, self.project.task_ids)

    def test_assign_task(self):
        task = self.engine.create_task("Task 1", "Desc", self.project.id, self.manager.id)
        self.engine.assign_task(task.id, self.user.id, self.manager.id)
        self.assertEqual(task.assigned_to, self.user.id)

    def test_assign_to_inactive_user(self):
        task = self.engine.create_task("Task 1", "Desc", self.project.id, self.manager.id)
        self.user.deactivate()
        with self.assertRaises(InactiveUserError):
            self.engine.assign_task(task.id, self.user.id, self.manager.id)

    def test_start_task(self):
        task = self.engine.create_task("Task 1", "Desc", self.project.id, self.manager.id)
        self.engine.assign_task(task.id, self.user.id, self.manager.id)
        self.engine.start_task(task.id, self.user.id)
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)

    def test_complete_task(self):
        task = self.engine.create_task("Task 1", "Desc", self.project.id, self.manager.id)
        self.engine.assign_task(task.id, self.user.id, self.manager.id)
        self.engine.start_task(task.id, self.user.id)
        self.engine.complete_task(task.id, self.user.id)
        self.assertEqual(task.status, TaskStatus.COMPLETED)

    def test_invalid_transition(self):
        task = self.engine.create_task("Task 1", "Desc", self.project.id, self.manager.id)
        with self.assertRaises(InvalidTaskTransitionError):
            self.engine.complete_task(task.id, self.manager.id)

    def test_dependency_blocks_start(self):
        task_a = self.engine.create_task("Task A", "Desc", self.project.id, self.manager.id)
        task_b = self.engine.create_task("Task B", "Desc", self.project.id, self.manager.id)
        self.engine.add_task_dependency(task_b.id, task_a.id, self.manager.id)
        self.engine.assign_task(task_b.id, self.user.id, self.manager.id)
        with self.assertRaises(TaskDependencyError):
            self.engine.start_task(task_b.id, self.user.id)

    def test_dependency_auto_unlock(self):
        task_a = self.engine.create_task("Task A", "Desc", self.project.id, self.manager.id)
        task_b = self.engine.create_task("Task B", "Desc", self.project.id, self.manager.id)
        self.engine.add_task_dependency(task_b.id, task_a.id, self.manager.id)
        self.assertEqual(task_b.status, TaskStatus.BLOCKED)

        self.engine.assign_task(task_a.id, self.user.id, self.manager.id)
        self.engine.start_task(task_a.id, self.user.id)
        self.engine.complete_task(task_a.id, self.user.id)
        self.assertEqual(task_b.status, TaskStatus.READY)

    def test_event_generation(self):
        task = self.engine.create_task("Task 1", "Desc", self.project.id, self.manager.id)
        events = self.engine.get_events()
        self.assertTrue(any(e.event_type.value == "TASK_CREATED" for e in events))

    def test_project_completion(self):
        task = self.engine.create_task("Task 1", "Desc", self.project.id, self.manager.id)
        self.engine.assign_task(task.id, self.user.id, self.manager.id)
        self.engine.start_task(task.id, self.user.id)
        self.engine.complete_task(task.id, self.user.id)
        self.assertEqual(self.project.status.value, "COMPLETED")


if __name__ == "__main__":
    unittest.main()