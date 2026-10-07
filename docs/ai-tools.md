# AI Tools and Audit

Read tools expose projects, tasks, members, events, and dependencies through
structured results. Write tools expose task creation, updates, assignment,
dependency changes, and workflow actions.

Tools never access SQLite. They receive the Brain engine and call its public
operations. This keeps business logic out of both the provider and the API.

Each intelligence operation records provider, operation, action, parameters,
permission mode, timestamp, result status, error details, and related entities
in `ai_audit_records`. Failed calls remain visible for investigation.

Automation depth limits and the Brain's existing idempotency and workflow
guards protect against uncontrolled action chains. A future retry coordinator
can build on these audit records without changing tool contracts.