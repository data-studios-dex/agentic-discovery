---
name: ask
description: Ask natural language questions about a discovery run answered by the DA_CL_Discovery_GovernanceReviewerAgent.
---

# /agentic-discovery:ask

Queries the discovery telemetry context using natural language. This command is executed by the **`DA_CL_Discovery_GovernanceReviewerAgent`** (subagent `agentic-discovery:governance-reviewer`).

### Workflow
1. Claude Code delegates this query to the subagent `agentic-discovery:governance-reviewer`.
2. The agent inspects `runs/<run_id>/state.json` and `runs/<run_id>/audit.jsonl`.
3. The agent analyzes table health scores, defect details, and recommends SQL remediation queries.

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
- `/agentic-discovery:ask How to fix defects in table orders?`
