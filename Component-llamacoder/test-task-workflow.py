# tests/test_task.py
import unittest
from brain import NEEKAEngine
from brain.task import TaskStatus
from brain.exceptions import InvalidTaskTransitionError


class TestTaskWorkflow(unittest.TestCase):
    def setUp(self):
        self.engine = NEEKAEngine()
        self.user = self.engine.create_user("Test User", "test@neeka.io")
        self.manager = self.engine.create_user("Manager", "manager@neeka.io")
        self.project = self.engine.create_project("Test Project", "Desc", self.manager.id)

    def test_todo_to_ready(self):
        task = self.engine.create_task("Task", "Desc", self.project.id, self.manager.id)
        task.status = TaskStatus.READY
        self.assertEqual(task.status, TaskStatus.READY)

    def test_ready_to_in_progress(self):
        task = self.engine.create_task("Task", "Desc", self.project.id, self.manager.id)
        task.status = TaskStatus.READY
        self.engine.assign_task(task.id, self.user.id, self.manager.id)
        self.engine.start_task(task.id, self.user.id)
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)

    def test_in_progress_to_blocked(self):
        task = self.engine.create_task("Task", "Desc", self.project.id, self.manager.id)
        task.status = TaskStatus.IN_PROGRESS
        task.status = TaskStatus.BLOCKED
        self.assertEqual(task.status, TaskStatus.BLOCKED)

    def test_blocked_to_in_progress(self):
        task = self.engine.create_task("Task", "Desc", self.project.id, self.manager.id)
        task.status = TaskStatus.BLOCKED
        task.status = TaskStatus.IN_PROGRESS
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)

    def test_completed_cannot_transition(self):
        task = self.engine.create_task("Task", "Desc", self.project.id, self.manager.id)
        task.status = TaskStatus.COMPLETED
        with self.assertRaises(InvalidTaskTransitionError):
            task.status = TaskStatus.IN_PROGRESS


if __name__ == "__main__":
    unittest.main()