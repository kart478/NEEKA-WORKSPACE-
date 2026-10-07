# tests/test_workflow.py
import unittest
from brain.workflow import Workflow
from brain.task import TaskStatus


class TestWorkflow(unittest.TestCase):
    def test_valid_transitions(self):
        self.assertTrue(Workflow.can_transition(TaskStatus.TODO, TaskStatus.READY))
        self.assertTrue(Workflow.can_transition(TaskStatus.READY, TaskStatus.IN_PROGRESS))
        self.assertTrue(Workflow.can_transition(TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED))
        self.assertTrue(Workflow.can_transition(TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED))
        self.assertTrue(Workflow.can_transition(TaskStatus.BLOCKED, TaskStatus.IN_PROGRESS))

    def test_invalid_transitions(self):
        self.assertFalse(Workflow.can_transition(TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS))
        self.assertFalse(Workflow.can_transition(TaskStatus.CANCELLED, TaskStatus.READY))
        self.assertFalse(Workflow.can_transition(TaskStatus.TODO, TaskStatus.COMPLETED))


if __name__ == "__main__":
    unittest.main()