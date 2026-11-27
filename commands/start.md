---
name: start
description: Interactive wizard that lists saved database connections, allows adding a new connection, selects tables, runs profiling and 6-dimension DQ audits, and outputs full audit reports.
---

# /agentic-discovery:start

Launches the interactive database discovery and quality governance wizard.

### Interactive Workflow
1. Displays the list of saved connections from `connections.json`.
2. Allows selecting a saved database OR adding a new database connection URL (with real-time connection test).
3. Prompts for schema name and optional table filters.
4. Prompts for execution mode:
   - `Both` (Profiling + 6-Dimension DQ Checks)
   - `Profiling` only
   - `Quality Checks` only
5. Runs pipeline across Gates G1 through G6 with real-time logs.
6. Presents full audit summary and clickable links to generated deliverables.
7. Automatically launches an interactive conversational NLP Q&A session where you can ask about violations, defects, and remediation.

### CLI Equivalent
```bash
python run.py start
```
