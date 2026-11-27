# 🛡️ `agentic-discovery` User Guide & Command Reference

An enterprise-grade, multi-agent database introspection, statistical profiling, and 6-dimension data quality auditing framework built for **Claude Code**.

---

## 📑 Table of Contents

1. [Overview & Architecture](#1-overview--architecture)
2. [Quick Installation](#2-quick-installation)
3. [Zero-Secret Connection Management](#3-zero-secret-connection-management)
   - [How Connection Profiles Work](#how-connection-profiles-work)
   - [Method 1: Interactive Wizard](#method-1-interactive-wizard-recommended)
   - [Method 2: Slash Command Inside Claude Code](#method-2-slash-command-inside-claude-code)
   - [Method 3: Direct CLI Registration](#method-3-direct-cli-registration)
   - [Method 4: Manual Template in `connections.json`](#method-4-manual-template-in-connectionsjson)
   - [Supported Database Dialects](#supported-database-dialects)
4. [Command Reference (Claude Code & Terminal CLI)](#4-command-reference)
   - [`/agentic-discovery:list-connections`](#1-agentic-discoverylist-connections)
   - [`/agentic-discovery:add-connection`](#2-agentic-discoveryadd-connection)
   - [`/agentic-discovery:start`](#3-agentic-discoverystart)
   - [`/agentic-discovery:run`](#4-agentic-discoveryrun)
   - [`/agentic-discovery:ask`](#5-agentic-discoveryask)
   - [`/agentic-discovery:test`](#6-agentic-discoverytest)
5. [Quality Gates (G1–G6) & Execution Lifecycle](#5-quality-gates-g1g6--execution-lifecycle)
6. [Deliverables & Report Outputs](#6-deliverables--report-outputs)
7. [Security & PreToolUse Hook Guardrails](#7-security--pretooluse-hook-guardrails)

---

## 1. Overview & Architecture

`agentic-discovery` operates natively inside Claude Code to provide autonomous database inspection, deep profiling, and compliance-grade data quality governance.

- **No MCP Server Overhead**: Uses standard, native database drivers (`sqlite3`, `psycopg2`, `snowflake-connector-python`, `SQLAlchemy`).
- **Autonomous Multi-Agent Collaboration**: Divided into 7 architectural sessions (S1–S7) with 6 strict Quality Gates (G1–G6).
- **Zero Secrets Tracked**: Passwords are never committed to version control; they are resolved strictly in-memory at runtime via environment variables or interactive masking (`getpass`).
- **Full Governance Auditing**: Complete execution telemetry is logged to `audit.jsonl` and rendered into a Claude-themed interactive dashboard.

---

## 2. Quick Installation

### In Claude Code (No Git Clone Required)

Any member of your workspace can install the plugin directly with one command:

```bash
claude plugin install agentic-discovery --marketplace data-studios-dex/agentic-discovery
```

Or inside an active Claude Code interactive session:

```text
/plugin install agentic-discovery --marketplace data-studios-dex/agentic-discovery
```

### Local Development / Standalone Execution

```bash
git clone https://github.com/data-studios-dex/agentic-discovery.git
cd agentic-discovery
pip install -r requirements.txt
```

---

## 3. Zero-Secret Connection Management

### How Connection Profiles Work

All database connections are defined in `connections.json`. Each entry is a **zero-secret template** containing metadata (host, port, database, user, schema), but **never storing plain-text passwords**.

At runtime, the password is dynamically resolved through a 3-tier fallback:
1. **Explicit parameter / prompt**: User enters the password securely via masked prompt (`getpass`).
2. **Profile-Specific Environment Variable**: e.g., `POSTGRES_DEV_PASSWORD`, `SNOWFLAKE_DW_PASSWORD`.
3. **Global Environment Variable**: `DB_PASSWORD`.

---

### Method 1: Interactive Wizard (Recommended)

Start the discovery wizard inside Claude Code or CLI:

```bash
python run.py start
```
*(Or inside Claude Code: `/agentic-discovery:start`)*

1. The terminal displays the list of existing saved connections.
2. Select the option: **`[N + 1] ➕ Register New Zero-Secret Connection Profile`**.
3. Follow the guided interactive prompts:
   - **Profile Name**: e.g., `analytics_dw`, `billing_stage`
   - **Database Dialect**: `postgresql`, `snowflake`, `oracle`, `mysql`, `sqlite`, or `mssql`
   - **Database Host**: e.g., `db.internal.company.com` or Snowflake account identifier
   - **Database Port**: Port number (defaults: `5432` for Postgres, `1521` for Oracle, `3306` for MySQL)
   - **Database Name**: e.g., `enterprise_dw`
   - **Username**: e.g., `reporting_agent`
   - **Target Schema**: e.g., `public`, `analytics`
4. The wizard tests connection reachability and saves the clean template into `connections.json`.

---

### Method 2: Slash Command Inside Claude Code

Inside your Claude Code session (`claude`), use the `/agentic-discovery:add-connection` slash command:

```text
/agentic-discovery:add-connection [name] [dialect] [host] [port] [database] [username] [schema]
```

**Example (PostgreSQL):**
```text
/agentic-discovery:add-connection crm_prod postgresql db-prod.company.internal 5432 crm_db app_user public
```

**Example (Snowflake):**
```text
/agentic-discovery:add-connection snowflake_analytics snowflake xy12345.us-east-1 443 ANALYTICS_DW BI_USER PUBLIC
```

---

### Method 3: Direct CLI Registration

You can add a connection profile non-interactively using the terminal CLI:

```bash
python run.py --add-conn <name> <dialect> <host> <port> <database> <user> <schema>
```

**Example:**
```bash
python run.py --add-conn billing_db postgresql 10.0.1.25 5432 billing_core svc_agent public
```

---

### Method 4: Manual Template in `connections.json`

You can directly add a profile entry into `connections.json`:

```json
{
  "analytics_postgres": {
    "name": "analytics_postgres",
    "dialect": "postgresql",
    "host": "postgres.internal.net",
    "port": 5432,
    "database": "analytics",
    "username": "query_svc",
    "schema": "public",
    "description": "Production Analytics Data Warehouse",
    "password_env_var": "ANALYTICS_POSTGRES_PASSWORD"
  }
}
```

Then in your environment (`.env` or shell):
```bash
export ANALYTICS_POSTGRES_PASSWORD="YourSecurePasswordHere"
```

---

### Supported Database Dialects

| Dialect | Connection Structure | Required Drivers |
| :--- | :--- | :--- |
| **SQLite** | `sqlite:///path/to/database.db` | Built-in Python `sqlite3` |
| **PostgreSQL** | `postgresql://user:pass@host:5432/dbname` | `psycopg2-binary` |
| **Snowflake** | `snowflake://user:pass@account/dbname/schema` | `snowflake-connector-python` |
| **Oracle** | `oracle+oracledb://user:pass@host:1521/?service_name=ORCL` | `oracledb` |
| **MySQL** | `mysql+pymysql://user:pass@host:3306/dbname` | `pymysql` |
| **MS SQL Server** | `mssql+pyodbc://user:pass@host:1433/dbname?driver=ODBC+Driver+17` | `pyodbc` |

---

## 4. Command Reference

All commands are available as **Slash Commands inside Claude Code** or as **CLI Commands in your terminal**.

### 1. `/agentic-discovery:list-connections`
Displays all configured database connection profiles with masked credentials, target hosts, and default schemas.

- **Claude Code:**
  ```text
  /agentic-discovery:list-connections
  ```
- **Terminal CLI:**
  ```bash
  python run.py list
  ```

---

### 2. `/agentic-discovery:add-connection`
Registers a new database connection template in `connections.json` with dialect verification.

- **Claude Code:**
  ```text
  /agentic-discovery:add-connection sales_db postgresql db.internal 5432 sales reporting public
  ```
- **Terminal CLI:**
  ```bash
  python run.py --add-conn sales_db postgresql db.internal 5432 sales reporting public
  ```

---

### 3. `/agentic-discovery:start`
Launches the **full interactive discovery wizard**. It guides you through connection selection, schema selection, table filters, execution mode (`Both`, `Profiling`, or `Checks`), and runs Gates G1 through G6 with real-time logs.

- **Claude Code:**
  ```text
  /agentic-discovery:start
  ```
- **Terminal CLI:**
  ```bash
  python run.py start
  ```

---

### 4. `/agentic-discovery:run`
Executes discovery headless on a specific connection profile without interactive prompts. Ideal for CI/CD pipelines, automated cron jobs, or scripted runs.

- **Claude Code:**
  ```text
  /agentic-discovery:run --conn postgres_dev --schema public --mode both
  ```
- **Terminal CLI:**
  ```bash
  # Run both Profiling and DQ Checks on sample DB:
  python run.py --conn sqlite_sample

  # Run on PostgreSQL with specific table filters:
  python run.py --conn postgres_dev --schema public --tables customers,orders --mode both
  ```

---

### 5. `/agentic-discovery:ask`
Queries the discovery telemetry context using natural language. It interrogates the generated `runs/<run_id>/state.json` and `audit.jsonl` to explain table health scores, defect details, schema architecture, and recommended SQL remediation scripts.

- **Post-Completion Live Q&A**:
  When you execute `/agentic-discovery:start` (or `python run.py --conn <name> --qa`), the system **automatically initiates an interactive Q&A session** immediately after reports are generated. You can freely ask questions until you type `exit`.

- **Claude Code Examples:**
  ```text
  /agentic-discovery:ask Show all data quality violations
  /agentic-discovery:ask Why is the orders table marked DEGRADED?
  /agentic-discovery:ask How to fix defects in table customers?
  /agentic-discovery:ask Show columns and structure of table products
  /agentic-discovery:ask Show overall table health scores
  /agentic-discovery:ask Which columns have missing null values?
  /agentic-discovery:ask Where are the report files saved?
  ```
- **Terminal CLI:**
  ```bash
  python run.py ask "Show all data quality violations"
  python run.py ask "How to fix defects in table customers?"
  python run.py --conn sqlite_sample --qa
  ```

---

### 6. `/agentic-discovery:test`
Executes the automated unit test suite and integration sanity checks to ensure drivers, SQL safety guards, and orchestrators are operational.

- **Claude Code:**
  ```text
  /agentic-discovery:test
  ```
- **Terminal CLI:**
  ```bash
  python run.py test
  ```

---

## 5. Quality Gates (G1–G6) & Execution Lifecycle

Every execution transitions through 6 distinct phases governed by strict, unbypassable Quality Gates:

```mermaid
flowchart LR
    G1["G1: Introspection\n(Discovers Schema)"] --> G2["G2: SQL Gen\n(19 Profiling Queries)"]
    G2 --> G3["G3: Execution\n(Non-Destructive Profiling)"]
    G3 --> G4["G4: Rulegen\n(6-Dim DQ Assertions)"]
    G4 --> G5["G5: Triage\n(Health Scoring)"]
    G5 --> G6["G6: Deliverables\n(HTML & Audit Trails)"]
```

1. **Gate G1 (Introspection)**: Introspects database engine metadata, retrieves tables, column data types, and primary/foreign keys.
2. **Gate G2 (Formulation)**: Synthesizes read-only statistical profiling queries (row counts, nulls, distincts, min/max).
3. **Gate G3 (Execution)**: Validates SQL queries with AST safety checks and executes them against the database.
4. **Gate G4 (DQ Rulegen)**: Synthesizes multi-dimension quality rules:
   - **Completeness**: Null rate thresholds.
   - **Uniqueness**: Primary key duplication checks.
   - **Validity**: Pattern checks (e.g. Email format, regex compliance).
   - **Timeliness / Consistency**: Date freshness and logical bounds.
5. **Gate G5 (Triage)**: Categorizes table health into:
   - 🟢 `HEALTHY` (Score ≥ 90%)
   - 🟡 `NEEDS_ATTENTION` (Score 70%–89%)
   - 🔴 `DEGRADED` (Score < 70% or critical key failures)
6. **Gate G6 (Deliverables)**: Compiles all governance assets and writes them to disk.

### Managed Agents Enterprise Naming Convention

All provisioned agents in `managed_agents.json` follow the standardized convention:
`DA_CL_{UseCase}_{AgentName}`

| Skill / Session | Standardized Managed Agent Identifier | Description |
| :--- | :--- | :--- |
| `discovery_orchestrator` | `DA_CL_Discovery_DiscoveryOrchestratorAgent` | Master hub-and-spoke pipeline orchestrator |
| `db_discovery` | `DA_CL_Discovery_DbDiscoveryAgent` | Database engine metadata & schema introspection |
| `sql_profiler` | `DA_CL_Discovery_SqlProfilerAgent` | Statistical data volume & distribution profiling |
| `sql_validator_fixer` | `DA_CL_Discovery_SqlValidatorFixerAgent` | AST validation, safety checks & self-healing |
| `dq_rulegen` | `DA_CL_Discovery_DqRuleGenAgent` | 6-dimension data quality rule synthesis |
| `governance_reviewer` | `DA_CL_Discovery_GovernanceReviewerAgent` | Table health classification & scoring |
| `governance_reporter` | `DA_CL_Discovery_GovernanceReporterAgent` | Multi-format reports & immutable audit trails |

---

## 6. Deliverables & Report Outputs

Every discovery execution writes its full audit bundle to `runs/<YYYYMMDD_HHMMSS>/`:

| File Name | Format | Content & Purpose |
| :--- | :--- | :--- |
| `discovery_report.html` | HTML | **Interactive Claude-themed dashboard** featuring health badges, table cards, pass/fail metrics, and interactive defect modals. |
| `AUDIT_REPORT.md` | Markdown | **Executive summary** ready for sharing in PRs, Jira issues, or Confluence pages. |
| `audit.jsonl` | JSON Lines | **Immutable telemetry stream** capturing every gate transition, query execution, latency, and violation. |
| `state.json` | JSON | **Structured state snapshot** used by the NLP Q&A engine for instant answers. |

---

## 7. Security & PreToolUse Hook Guardrails

The plugin includes an active security hook (`hooks/hooks.json` & `hooks/sql_safety_guard.py`):

- **PreToolUse Bash Guard**: Automatically inspects terminal commands before execution.
- **SQL Mutation Blocker**: Queries containing destructive statements (`DROP`, `TRUNCATE`, `DELETE`, `ALTER`, `GRANT`, `INSERT`, `UPDATE`) are rejected before they reach the database.
- **Read-Only Enforcement**: Guarantees that discovery and profiling never modify schema definitions or table contents.
