# 🛡️ Enterprise Agentic Database Discovery & Quality Governance (`agentic-discovery`)

Autonomous, multi-agent database introspection, statistical profiling, and 6-dimension data quality auditing engine. Implements the **7 Architectural Sessions (S1–S7)** and unbypassable **Quality Gates (G1–G6)**.

Packaged as a native **Claude Code Plugin** without requiring an external MCP server, and runnable locally in the terminal with zero external dependencies.

---

## 🌟 Highlights

- **Multi-Database Direct Connectivity**: Connects directly to SQLite, PostgreSQL, Snowflake, Oracle, MySQL, and Microsoft SQL Server.
- **Connection Profile Registry (`connections.json`)**: Manage multiple saved connection profiles, test connection reachability, and add new connections dynamically.
- **Pure Managed Agents Architecture**: Provisioned versioned subagents recorded in `managed_agents.json`.
- **Full Auditing (S5)**: Comprehensive real-time telemetry, gate decisions, SQL execution log, and violation tallies stored in `audit.jsonl`.
- **Claude-Themed Interactive Dashboard**: Executive health scoring, table triage, and interactive rule defect analysis.
- **Strict Quality Gates (G1–G6)**: G1 Discovery ➔ G2 Profile SQL ➔ G3 Execution ➔ G4 DQ Assertions ➔ G5 Health Triage ➔ G6 Governance Deliverables.
