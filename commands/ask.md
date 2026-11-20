---
name: ask
description: Ask natural language questions about the latest database discovery and data quality run (health triage, violation root causes, row counts, recommendations).
---

# /agentic-discovery:ask

Interactively answers user questions using the discovery and audit telemetry context.

### Syntax
```bash
/agentic-discovery:ask [question]
```

### Examples
- `/agentic-discovery:ask Why is the orders table marked DEGRADED?`
- `/agentic-discovery:ask Are there any duplicate primary keys?`
- `/agentic-discovery:ask Which columns have missing null values?`
- `/agentic-discovery:ask Where are the report files saved?`

### CLI Equivalent
```bash
python run.py ask "Why is table orders DEGRADED?"
```
