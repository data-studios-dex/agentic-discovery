---
name: ask
description: Ask natural language questions about a specific discovery run (e.g. 20261127T104512_shop) or the latest run.
---

# /agentic-discovery:ask

Queries the discovery telemetry context using natural language. It interrogates the specified run's `state.json` and `audit.jsonl` to explain table health scores, defect details, schema architecture, and recommended SQL remediation scripts.

### Syntax
```bash
/agentic-discovery:ask [run_id] [question]
/agentic-discovery:ask --run-id <run_id> [question]
```

### Examples
- `/agentic-discovery:ask 20261127T104512_shop Show all data quality violations`
- `/agentic-discovery:ask 20261127T104512_shop Why is the orders table marked DEGRADED?`
- `/agentic-discovery:ask 20261127T104512_shop How to fix defects in table customers?`
- `/agentic-discovery:ask Show all data quality violations`
- `/agentic-discovery:ask Why is the orders table marked DEGRADED?`
- `/agentic-discovery:ask How to fix defects in table customers?`
- `/agentic-discovery:ask Show structure and columns of table products`
- `/agentic-discovery:ask Show overall table health status and scores`

### Interactive Mode
To start a continuous interactive Q&A session on a specific run without typing the command repeatedly:
```bash
/agentic-discovery:qa 20261127T104512_shop
```

### CLI Equivalent
```bash
python run.py ask --run-id 20261127T104512_shop "Show all data quality violations"
python run.py ask 20261127T104512_shop "Why is table orders DEGRADED?"
python run.py qa 20261127T104512_shop
```
