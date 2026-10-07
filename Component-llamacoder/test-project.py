# tests/test_project.py
import unittest
from brain import NEEKAEngine
from brain.project import ProjectStatus


class TestProject(unittest.TestCase):
    def setUp(self):
        self.engine = NEEKAEngine()
        self.manager = self.engine.create_user("Manager", "manager@neeka.io")
        self.user = self.engine.create_user("User", "user@neeka.io")

    def test_project_creation(self):
        project = self.engine.create_project("Project", "Desc", self.manager.id)
        self.assertEqual(project.status, ProjectStatus.PLANNED)
        self.assertIn(self.manager.id, project.member_ids)

    def test_project_members(self):
        project = self.engine.create_project("Project", "Desc", self.manager.id)
        self.engine.add_project_member(project.id, self.user.id, self.manager.id)
        self.assertEqual(len(project.member_ids), 2)

    def test_project_completion(self):
        project = self.engine.create_project("Project", "Desc", self.manager.id)
        task = self.engine.create_task("Task", "Desc", project.id, self.manager.id)
        self.engine.assign_task(task.id, self.user.id, self.manager.id)
        self.engine.start_task(task.id, self.user.id)
        self.engine.complete_task(task.id, self.user.id)
        self.assertEqual(project.status, ProjectStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()