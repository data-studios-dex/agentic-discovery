# 🛡️ Enterprise Agentic Database Discovery & Quality Governance (`agentic-discovery`)
## Official Claude Code Plugin & Multi-Agent Architecture (No MCP Required)

### Overview
Autonomous multi-agent framework for dynamic database introspection, statistical profiling, 6-dimension data quality audits, and self-healing query execution across the 7 architectural sessions (**S1–S7**):
- **S1 (Agentic Loop)**: `generate ➔ validate ➔ execute ➔ (fix ➔ re-validate)*` for SQL queries in [`core/loop.py`](core/loop.py).
- **S2 (Hub-and-Spoke Orchestration)**: Centrally governed by `DiscoveryOrchestrator` in [`core/orchestrator.py`](core/orchestrator.py).
- **S3 (Strict Context Passing)**: Strongly typed dataclasses in [`core/schemas.py`](core/schemas.py).
- **S4 (Step Enforcement)**: Unbypassable quality gates G1–G6 in [`core/gates.py`](core/gates.py).
- **S5 (Hooks & Safety Guardrails)**: Safety checks and continuous telemetry in [`hooks/hooks.json`](hooks/hooks.json) and `runs/<run_id>/audit.jsonl`.
- **S6 (Adaptive Fan-Out)**: Per-table profiling with fault isolation.
- **S7 (State & Resumability)**: Checkpoint-based state persistence (`state.json`) with `--resume`.

---

## 🔌 Connection Profiles & Management

All database connections are registered in [`connections.json`](connections.json):
- SQLite (`sqlite_sample`)
- PostgreSQL (`postgres_dev`)
- Snowflake (`snowflake_dw`)
- Oracle (`oracle_billing`)
- MySQL (`mysql_ecommerce`)
- Easily add new connections interactively via `python run.py start` or CLI `python run.py --add-conn`.

---

## 📦 Claude Code Native Plugin Architecture

This plugin runs **purely native without requiring an external MCP server**:
- Subagents in [`agents/*.md`](agents/) execute directly within Claude Code.
- Skills in [`skills/*/SKILL.md`](skills/) adhere to the Anthropic Agent Skills standard.
- Slash commands in [`commands/*.md`](commands/) provide instant developer shortcuts (`/agentic-discovery:start`, `/agentic-discovery:list-connections`, etc.).
- Control Plane registry in [`managed_agents.json`](managed_agents.json) tracks provisioned Claude Managed Agents.

---

## 🚀 How to Run and Test

### 1. Interactive Wizard in Terminal
```bash
python run.py start
```

### 2. CLI Direct Run with Connection Profile
```bash
python run.py --conn sqlite_sample
```

### 3. List and Add Connections
```bash
python run.py --list-conns
python run.py --add-conn my_postgres "postgresql://user:pass@localhost:5432/mydb" public "Production Postgres"
```

### 4. Load in Claude Code
```bash
claude --plugin-dir c:\Users\saikiran.chandana\Desktop\Claude\agentic_discovery
```
Available slash commands:
- `/agentic-discovery:start`
- `/agentic-discovery:list-connections`
- `/agentic-discovery:add-connection`
- `/agentic-discovery:run [conn_name]`
- `/agentic-discovery:test`
