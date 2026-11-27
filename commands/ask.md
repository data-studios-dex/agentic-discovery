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
- `/agentic-discovery:ask Show all data quality violations`
- `/agentic-discovery:ask Why is the orders table marked DEGRADED?`
- `/agentic-discovery:ask How to fix defects in table customers?`
- `/agentic-discovery:ask Show structure and columns of table products`
- `/agentic-discovery:ask Show overall table health status and scores`
- `/agentic-discovery:ask Are there any duplicate primary keys?`
- `/agentic-discovery:ask Which columns have missing null values?`
- `/agentic-discovery:ask Where are the report files saved?`

### Interactive Post-Run Mode
The Q&A session automatically activates after running `/agentic-discovery:start`, allowing you to ask questions in real-time right after the audit finishes.

### CLI Equivalent
```bash
python run.py ask "Show all data quality violations"
python run.py --conn sqlite_sample --qa
```
