---
name: qa
description: Launch an interactive, continuous conversational Q&A session locked to a specific run ID (e.g. 20261127T104512_shop) or the latest run.
---

# /agentic-discovery:qa

Launches an interactive natural language Q&A session where you can ask continuous questions about table health, data quality violations, schema architecture, and SQL remediation.

### Syntax
```bash
/agentic-discovery:qa [run_id]
```

### Examples
- `/agentic-discovery:qa 20261127T104512_shop`
- `/agentic-discovery:qa` (defaults to latest discovery run)

### CLI Equivalent
```bash
python run.py qa 20261127T104512_shop
python run.py qa
```
