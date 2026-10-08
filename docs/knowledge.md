# Project Knowledge

Project Knowledge is persistent project information, separate from work state.
It is stored and governed by NEEKA; Intelligence may consume bounded context
but does not own the information or access SQLite directly.

## Entities

- Documents contain structured text, type, status, metadata, and version history.
- Requirements capture project expectations, priority, source, and lifecycle.
- Decisions capture the choice, reason, alternatives, status, and supersession.
- Notes are lightweight authored project observations with reusable tags.
- References store external URLs and descriptions; NEEKA does not fetch them.

Documents use `document_versions`, so an update creates a new version while the
current document points to the latest content. Relationships are represented by
`knowledge_relationships` and can link requirements or decisions to tasks,
projects, documents, and other supported entities.

## Access And API

Knowledge reads and writes require a project member actor. The API provides
project-scoped document, requirement, decision, note, reference, aggregate,
and keyword-search endpoints under `/api/v1`. Routes delegate to the engine
and knowledge service. Important changes use the existing event repository.

SQLite migration v4 creates the tables, indexes, tags, entity tags, and
relationships. Search supports keyword, project, type, and status filters.

## Intelligence And Future Work

`ContextBuilder` exposes separate bounded knowledge collections to the
Intelligence Layer. The current implementation deliberately has no vector
database, embeddings, cloud file storage, or unrestricted AI retrieval. A later
step can add document adapters and a retrieval index behind the same knowledge
service without changing the Brain or giving providers database access.