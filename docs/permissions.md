# Intelligence Permissions

## READ_ONLY

Analysis, planning, and read tools are available. Write tools are rejected.

## ASSISTED

The gateway can propose and validate write actions, but the caller must send
`approved: true` before a write tool executes.

## AUTONOMOUS

Permitted write tools may execute without interactive approval. They still call
the Brain, which enforces membership, task dependencies, workflow transitions,
inactive-user rules, and automation safety.

Authentication is intentionally a seam in this phase. The API has a dependency
placeholder so authentication can be added without changing route handlers.