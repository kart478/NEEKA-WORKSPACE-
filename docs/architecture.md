# NEEKA Architecture

NEEKA is layered so the Brain remains the authority for work state:

```text
Client/API -> Intelligence Gateway -> Application Services -> Brain
           -> Workflow/Automation -> Repositories -> SQLite
```

The API and Intelligence layers do not issue SQL. Intelligence tools call the
existing Brain methods, so workflow rules, dependencies, permissions, events,
and persistence remain centralized.

Part 5 adds provider-neutral analysis, planning, controlled tools, permission
modes, and persisted AI audit records. The mock provider is deterministic and
requires no credentials.