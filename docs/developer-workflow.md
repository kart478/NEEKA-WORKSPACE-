# Developer Workflow Pack

Developer workflow metadata is optional and belongs to an existing task. Its human-readable stage maps to the existing global `TaskStatus`, so all established task rules remain in effect.

Supported workflows are `feature`, `bug`, `code_review`, and `release`. Use `POST /api/v1/tasks/{task_id}/dev-metadata` to attach metadata, then `POST /api/v1/tasks/{task_id}/dev-transition` to move to the next stage. Read metadata with `GET /api/v1/tasks/{task_id}/dev-metadata` and list a project's developer tasks with `GET /api/v1/projects/{project_id}/dev-tasks`.

Completion safeguards are enforced by the engine:

- Bugs with test requirements require a verification result.
- Code-review tasks require a recorded review outcome.
- Release tasks require all listed blocking tasks to be completed.

The Engineering desktop view renders the live project workflow board. Developer intelligence tools are read-only and return structured planning, bug-summary, release-readiness, and release-note proposals.
