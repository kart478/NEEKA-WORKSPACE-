# Intelligence Layer

`IntelligenceGateway` is the single entry point for analysis, planning, and
actions. It builds bounded project context with `ContextBuilder`, delegates
reasoning to an `AIProvider`, validates structured output, and invokes tools.

Providers implement `generate`, `analyze`, and `plan`. `MockAIProvider` is used
for local development and tests; a hosted or local provider can be added without
changing the gateway.

Actions are structured as an action name plus parameters. Unknown tools,
malformed parameters, invalid IDs, and Brain validation failures are rejected.
Every attempt is written to the AI audit repository.

The current knowledge foundation is deliberately small. Project context can be
now include bounded documents, requirements, decisions, notes, and references
as separate structured collections. Read-only knowledge tools call the Brain
query surface and respect project membership. This keeps project knowledge
owned by NEEKA rather than by the AI provider.

Search is currently SQLite keyword search. Embeddings, vector indexes, cloud
document storage, and full RAG retrieval are intentionally deferred to a later
architecture step.