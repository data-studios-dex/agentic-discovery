---
name: qa
description: Launch an interactive conversational Q&A session powered by the DA_CL_Discovery_GovernanceReviewerAgent.
---

# /agentic-discovery:qa

Launches an interactive, continuous conversational Q&A session powered by **`DA_CL_Discovery_GovernanceReviewerAgent`** (subagent `agentic-discovery:governance-reviewer`).

### Workflow
1. Claude Code activates `agentic-discovery:governance-reviewer`.
2. The agent loads the run context for the specified `run_id` (or latest run).
3. The agent continuously responds to your natural language questions about table health, data quality violations, and SQL remediation.

### Syntax
```bash
/agentic-discovery:qa [run_id]
```

### Examples
- `/agentic-discovery:qa 20261127T104512_shop`
- `/agentic-discovery:qa`
