import pytest

from neeka import NEEKAEngine
from neeka.brain.dev_workflow import DevMetadata, WorkflowType
from neeka.brain.exceptions import InvalidWorkflowStageError, ReleaseBlockedError, VerificationRequiredError
from neeka.brain.task import TaskStatus


def setup_engine(tmp_path):
    engine = NEEKAEngine(tmp_path / "dev-workflow.db")
    owner = engine.create_user("Owner", "owner@example.com")
    project = engine.create_project("Project", "", owner.id)
    return engine, owner, project


def test_feature_stage_transition_persists(tmp_path):
    engine, owner, project = setup_engine(tmp_path)
    task = engine.create_task("Feature", "", project.id, owner.id)
    engine.create_dev_metadata(task.id, owner.id, DevMetadata(task_id=task.id))
    engine.transition_dev_stage(task.id, "Ready", owner.id)
    engine.transition_dev_stage(task.id, "In Progress", owner.id)

    assert engine.get_task(task.id).status == TaskStatus.IN_PROGRESS
    assert engine.get_dev_metadata(task.id, owner.id).stage == "In Progress"
    with pytest.raises(InvalidWorkflowStageError):
        engine.transition_dev_stage(task.id, "Done", owner.id)


def test_bug_requires_verification_and_release_requires_completed_blockers(tmp_path):
    engine, owner, project = setup_engine(tmp_path)
    bug = engine.create_task("Bug", "", project.id, owner.id)
    engine.create_dev_metadata(bug.id, owner.id, DevMetadata(
        task_id=bug.id, workflow_type=WorkflowType.BUG, stage="Reported", test_requirements="Regression test",
    ))
    with pytest.raises(VerificationRequiredError):
        engine.complete_task(bug.id, owner.id)

    blocker = engine.create_task("Blocker", "", project.id, owner.id)
    release = engine.create_task("Release", "", project.id, owner.id)
    engine.create_dev_metadata(release.id, owner.id, DevMetadata(
        task_id=release.id, workflow_type=WorkflowType.RELEASE, stage="Planned", blocking_task_ids=[blocker.id],
    ))
    with pytest.raises(ReleaseBlockedError):
        engine.complete_task(release.id, owner.id)


def test_dev_metadata_round_trips_after_restart(tmp_path):
    engine, owner, project = setup_engine(tmp_path)
    task = engine.create_task("Review", "", project.id, owner.id)
    engine.create_dev_metadata(task.id, owner.id, DevMetadata(
        task_id=task.id, workflow_type=WorkflowType.CODE_REVIEW, stage="Requested", review_outcome="approved",
    ))
    restarted = NEEKAEngine(tmp_path / "dev-workflow.db")
    metadata = restarted.get_dev_metadata(task.id, owner.id)
    assert metadata.workflow_type == WorkflowType.CODE_REVIEW
    assert metadata.review_outcome == "approved"
