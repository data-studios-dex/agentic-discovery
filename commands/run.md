---
name: run
description: Run the full autonomous database discovery and DQ audit pipeline against a selected connection profile.
---

# /agentic-discovery:run

Executes the pipeline directly using a named connection profile.

### Syntax
```bash
/agentic-discovery:run [connection_name] [schema] [mode]
```

### Examples
```bash
/agentic-discovery:run sqlite_sample main both
/agentic-discovery:run postgres_dev public both
```
