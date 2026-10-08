# Workspace Artifacts

Artifacts are the files and work products used by NEEKA projects. They are
separate from Knowledge: Knowledge explains work, while Artifacts contain the
actual resources and outputs.

## Architecture

The application flow is:

```text
API -> NEEKAEngine -> ArtifactService -> ArtifactRepository
                                  -> ArtifactStorage -> LocalArtifactStorage
```

The domain receives artifact IDs and file streams. It never accepts arbitrary
filesystem paths, and Intelligence tools can request metadata or relationships
only through the engine.

The local storage root is application-managed. Files are stored under
`data/artifacts/<project_id>/<artifact_id>/versions/<version>/<filename>` for a
file-backed database, with the database directory used as the parent. Storage
keys are normalized and rejected if they are absolute, contain traversal, or
escape the root. Writes use a temporary file and atomic replacement.

## Versioning And Integrity

Each upload creates an `artifact_versions` record. New versions preserve prior
content and receive a SHA-256 checksum. Downloads verify the current checksum
before opening the controlled file. Duplicate content can be identified by
project and checksum without merging artifacts.

Artifacts have `PENDING`, `AVAILABLE`, `ARCHIVED`, `DELETED`, and `FAILED`
statuses. Deletion is currently a database-level soft delete; historical files
remain available for future reconciliation and retention policies.

## Relationships And Access

Artifacts can be attached to projects, tasks, Knowledge documents,
requirements, and decisions through a role such as `INPUT`, `OUTPUT`,
`REFERENCE`, or `ATTACHMENT`. Project membership controls reads, writes,
downloads, and relationship operations. Events use the existing event system.

The API supports multipart upload, project/task listing, metadata, download by
artifact ID, version creation/restoration, deletion, and relationship routes.
`ARTIFACT_MAX_SIZE` configures the default 50 MiB upload limit.

## Security And Future Work

Uploaded code is treated as data and is never executed. Raw filesystem paths are
never returned by the API, and AI has no direct filesystem or database access.
Cloud storage, previews, PDF/DOCX extraction, spreadsheet analysis, semantic
indexing, and AI artifact analysis remain extension points. Metadata extraction
is available; content extraction explicitly reports that it is not implemented.
