# 📘 Enterprise Claude Plugin Guide: Creation, Distribution & Usage

**Target Audience:** Enterprise Engineering & Data Architecture Teams  
**Workspace:** Dev-Data&Insights  
**Author:** Dev-Data&Insights Team  

---

## 📑 Table of Contents
1. [Executive Overview](#1-executive-overview)
2. [Architectural Options for Creating a Plugin](#2-architectural-options-for-creating-a-plugin)
3. [Step-by-Step Guide: Creating a Plugin from Scratch](#3-step-by-step-guide-creating-a-plugin-from-scratch)
4. [Distribution: How Workspace Members Add & Use It](#4-distribution-how-workspace-members-add--use-it)
5. [In-Depth Comparison: Normal Claude Chat vs. Claude CLI (Claude Code)](#5-in-depth-comparison-normal-claude-chat-vs-claude-cli-claude-code)
6. [Security & Zero-Secrets Hygiene (ADO Git Standards)](#6-security--zero-secrets-hygiene-ado-git-standards)
7. [Operational Cheat Sheet](#7-operational-cheat-sheet)

---

## 1. Executive Overview

A **Claude Plugin** is a structured, versioned customization bundle that extends Claude's reasoning with specialized subagents, domain skills, developer slash commands, and deterministic execution tools.

In enterprise data environments (such as database profiling, data quality auditing, and schema mapping), plugins allow teams to standardize repeatable workflows, eliminate manual setup, and enforce security policies across all members of a Claude Console Workspace (e.g., `Dev-Data&Insights`).

```
┌────────────────────────────────────────────────────────────────────────┐
│                   CLAUDE PLUGIN PACKAGE LAYOUT                         │
├───────────────────┬────────────────────────────────────────────────────┤
│ .claude-plugin/   │ Manifest metadata (name, version, author)          │
│ agents/           │ Subagent specifications (*.md)                     │
│ skills/           │ Modular Anthropic Agent Skills (skills/*/SKILL.md) │
│ commands/         │ Developer Slash Commands (commands/*.md)           │
│ hooks/            │ PreToolUse / PostToolUse safety guardrails         │
│ connections.json  │ Zero-secret connection templates                   │
│ core/             │ Deterministic Python engine & Quality Gates        │
│ run.py            │ Interactive CLI runner & automated self-healing    │
└───────────────────┴────────────────────────────────────────────────────┘
```

---

## 2. Architectural Options for Creating a Plugin

When designing an enterprise plugin, you have three primary architectural choices:

### Option A: Pure Native Plugin (Recommended for CLI & Script Automation)
* **How it works:** Does **not** require a background daemon or Model Context Protocol (MCP) server. Claude Code interacts directly with the local codebase via its built-in tools (`Bash`, `Read`, `Write`) and modular skills.
* **Pros:**
  - Zero background processes; no stdio pipe disconnects or zombie daemon issues.
  - 100% testable directly in any standard terminal (`python run.py start`).
  - Supports interactive terminal password prompting (`getpass`) so zero credentials are saved.
* **Best for:** Database profiling, ETL code generation, data quality auditing, migrations.

### Option B: MCP-Powered Plugin (Best for Claude Desktop GUI)
* **How it works:** Includes an embedded Model Context Protocol (MCP) server (`mcp_server.py`) that runs as a JSON-RPC 2.0 stdio server, exposing registered tools directly into Claude’s tool palette.
* **Pros:** Exposes discrete tool buttons directly inside the Claude Desktop application UI.
* **Cons:** Requires a persistent background daemon; credential handling requires careful parameter passing.
* **Best for:** Interactive graphical desktop environments.

### Option C: Hybrid Plugin
* **How it works:** Exposes both native subagents/skills for Claude Code CLI and an optional MCP server configuration for Claude Desktop GUI users.
* **Best for:** Organizations with mixed developer tooling (some developers in terminal, some on desktop UI).

---

## 3. Step-by-Step Guide: Creating a Plugin from Scratch

### Step 1: Initialize the Plugin Manifest
Create `.claude-plugin/plugin.json`:
```json
{
  "name": "agentic-discovery",
  "version": "1.0.0",
  "description": "Enterprise autonomous database discovery and DQ auditing framework.",
  "author": "Dev-Data&Insights Team"
}
```

### Step 2: Define Specialized Subagents (`agents/`)
Subagents are defined in Markdown files with YAML frontmatter specifying their name, description, and permitted tools:
* `agents/discovery-orchestrator.md`: Master coordinator managing pipeline state and gates G1–G6.
* `agents/db-discovery.md`: Dynamic catalog and table introspection subagent.
* `agents/sql-profiler.md`: Statistical data profiling subagent.
* `agents/dq-rulegen.md`: 6-dimension data quality assertion generator.
* `agents/sql-validator-fixer.md`: Read-only AST validator and query repair subagent.
* `agents/governance-reviewer.md`: Health scoring and defect classification subagent.
* `agents/governance-reporter.md`: Multi-format deliverable and audit builder.

### Step 3: Implement Modular Agent Skills (`skills/`)
Each subagent possesses an Anthropic Agent Skill adhering to the standard `skills/<skill_name>/SKILL.md`:
```markdown
---
name: db_discovery
description: Introspects database schemas, table structures, column definitions, and row counts dynamically.
version: 1.0.0
tools: ["Bash", "Read"]
---

# Database Discovery Skill
Contains instructions on formulating catalog queries across SQLite, PostgreSQL, Snowflake, Oracle, and MySQL.
```

### Step 4: Configure Developer Slash Commands (`commands/`)
Slash commands provide one-line shortcuts in chat:
* `/agentic-discovery:start`: Launches the interactive wizard (select connection, choose mode, run).
* `/agentic-discovery:ask`: Allows natural language questions on run results.
* `/agentic-discovery:list-connections`: Lists saved database connection templates.
* `/agentic-discovery:add-connection`: Registers a new database connection profile.
* `/agentic-discovery:run [conn_name]`: Directly executes against a saved profile.

### Step 5: Establish Pre/Post-Tool Safety Hooks (`hooks/`)
Configure `hooks/hooks.json` to block destructive SQL statements:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "description": "Block destructive commands (DROP, DELETE, TRUNCATE, ALTER, INSERT, UPDATE)",
        "command": "python hooks/sql_safety_guard.py"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "description": "Log tool execution telemetry to audit.jsonl"
      }
    ]
  }
}
```

### Step 6: Configure Zero-Secret Connection Templates (`connections.json`)
Store connection metadata without passwords:
```json
{
  "postgres_dev": {
    "name": "postgres_dev",
    "dialect": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "crm_dev",
    "username": "postgres",
    "schema": "public",
    "password_env_var": "POSTGRES_PASSWORD"
  }
}
```

---

## 4. Distribution: How Workspace Members Add & Use It

### Method A: Azure DevOps (ADO) Git Private Marketplace (Enterprise Recommended)
This method allows members of `Dev-Data&Insights` to install and update the plugin with one command.

#### Step 1: Host the Plugin in an ADO Git Repository
Create an ADO repository:
```bash
https://dev.azure.com/YourOrg/Dev-Data-Insights/_git/agentic-discovery
```
Push the plugin folder directly to the `main` branch:
```bash
git init
git add .
git commit -m "feat: enterprise agentic discovery plugin"
git remote add origin https://dev.azure.com/YourOrg/Dev-Data-Insights/_git/agentic-discovery
git push -u origin main
```

#### Step 2: Member Adds Marketplace in Claude CLI
Any member in your workspace opens their terminal and adds the ADO repository:
```bash
/plugin marketplace add https://dev.azure.com/YourOrg/Dev-Data-Insights/_git/agentic-discovery
```
*(Windows Git Credential Manager authenticates the member via corporate Azure Active Directory single sign-on automatically).*

#### Step 3: Member Installs the Plugin
```bash
/plugin install agentic-discovery@agentic-discovery
```

#### Step 4: Receiving Daily Updates
Whenever changes are pushed to ADO Git, members run:
```bash
/plugin update agentic-discovery
```

---

### Method B: Shared Project Clone Mode (Direct Git Pull)
If team members work within a shared monorepo or project repository:
1. Include the `agentic_discovery/` folder in the project repo.
2. Team members pull changes daily:
   ```bash
   git pull origin main
   ```
3. Members start Claude Code pointing to the folder:
   ```bash
   claude --plugin-dir ./agentic_discovery
   ```

---

### Method C: Claude Console Workspace Scoping
To ensure all API calls and Managed Agents are billed and managed under the `Dev-Data&Insights` workspace:
1. Open **Claude Console** (`https://platform.claude.com/settings/workspaces`).
2. Select **`Dev-Data&Insights`** (ID: `wrkspc_01EaNE1wTn8Sf1q6pj1Hbasx`).
3. Generate an API Key under this workspace.
4. Set the key in your local `.env`:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ```
5. All members using this workspace key share the provisioned Managed Agents tracked in `managed_agents.json`.

---

## 5. In-Depth Comparison: Normal Claude Chat vs. Claude CLI (Claude Code)

Understanding the operational differences between the browser-based chat interface and the developer CLI is critical for architecture decisions:

| Feature / Dimension | Normal Claude Chat (Web / Mobile) | Claude Desktop App (with MCP) | Claude CLI / Claude Code |
|---|---|---|---|
| **Primary Interface** | Web browser (`claude.ai`) | Desktop Electron application | Terminal / Shell (`claude`) |
| **Local File System Access** | ❌ No direct local file access (upload attachments only) | ⚠️ Partial (via configured MCP server roots) | ✅ **Full, native access** to local workspace files |
| **Local Database Connectivity** | ❌ None (cannot connect to internal DBs/VPNs) | ⚠️ Indirect (requires active local MCP daemon) | ✅ **Direct Python connectivity** (`SQLAlchemy`, `sqlite3`, ODBC) |
| **Terminal & Command Execution** | ❌ None | ❌ None | ✅ **Full execution** (`run_command`, `Bash`, CLI tools) |
| **Subagent Task Delegation** | ❌ Single-agent conversational thread | ❌ Single-agent with tool calls | ✅ **Hub-and-spoke multi-agent** delegation (`agents/*.md`) |
| **Quality Gate Enforcement (S4)** | ❌ Relies solely on prompt suggestions | ⚠️ Limited to MCP tool schemas | ✅ **Strict programmatic gates G1–G6** halting invalid steps |
| **Iterative Self-Healing (S1)** | ⚠️ Manual copy-paste of error messages | ⚠️ Dependent on tool return loops | ✅ **Autonomous multi-attempt repair loops** (`loop.py`) |
| **Output Deliverables** | Chat markdown text | Chat markdown + local file writes | **Full artifacts**: `.html` dashboards, `.md`, `.jsonl`, `.xlsx` |
| **Interactive Terminal Wizard** | ❌ Form-based UI only | ❌ None | ✅ **Rich interactive CLI** (`python run.py start`, `getpass`) |
| **Natural Language Q&A Engine** | General assistant reasoning | General assistant with MCP context | **Targeted Q&A** against `audit.jsonl` and `state.json` |

---

## 6. Security & Zero-Secrets Hygiene (ADO Git Standards)

To comply with enterprise security auditing, this framework strictly prevents credential leakage into Git:

```
┌────────────────────────────────────────────────────────┐
│               ZERO-SECRETS HYGIENE IN ADO              │
├─────────────────────────┬──────────────────────────────┤
│ connections.json        │ Contains host/user metadata; │
│ (Tracked in Git)        │ ZERO passwords stored.       │
├─────────────────────────┼──────────────────────────────┤
│ .env                    │ Contains local API keys/DB   │
│ (IGNORED by .gitignore) │ passwords; never committed.  │
├─────────────────────────┼──────────────────────────────┤
│ Terminal Prompt         │ Prompts password with        │
│ (getpass masking)       │ hidden input at runtime.     │
├─────────────────────────┼──────────────────────────────┤
│ runs/ and reports/      │ Stored locally; excluded     │
│ (IGNORED by .gitignore) │ from git commits.            │
└─────────────────────────┴──────────────────────────────┘
```

1. **Password Masking at Runtime**:
   When connecting to databases, the CLI invokes Python's `getpass` module:
   ```text
   Enter password for postgres_dev (postgres@localhost): *********
   ```
   The password is used purely in memory to construct the SQLAlchemy session and is **never written to `connections.json`**.

2. **Environment Variable Fallback**:
   In automated CI/CD pipelines, passwords can be passed via environment variables matching the profile:
   ```bash
   export POSTGRES_DEV_PASSWORD="MySecurePassword123"
   python run.py --conn postgres_dev
   ```

3. **Packaging Security Gate**:
   `package_plugin.py` automatically scans every file for patterns matching API keys, database credentials, or private keys before building the upload bundle.

---

## 7. Operational Cheat Sheet

### Common CLI Commands
```bash
# 1. Start the interactive wizard
python run.py start

# 2. Run directly against a saved profile
python run.py --conn sqlite_sample

# 3. List all saved connection profiles
python run.py --list-conns

# 4. Add a new connection template
python run.py --add-conn stage_pg postgresql localhost 5432 stg_db app_user public

# 5. Ask natural language questions about the latest run
python run.py ask "Why is table orders DEGRADED?"
python run.py ask "How many total rows were discovered?"
python run.py ask "Where are the reports saved?"

# 6. Verify Managed Agents registry synchronization
python run.py --check-managed-agents

# 7. Run unit test suite
python -m unittest tests/test_discovery_pipeline.py -v
```

### Common Claude Code Slash Commands
```bash
/agentic-discovery:start             # Run interactive wizard in chat
/agentic-discovery:list-connections  # View saved database connections
/agentic-discovery:run [conn_name]   # Execute discovery on connection profile
/agentic-discovery:ask [question]    # Ask questions on profiling and DQ defects
/agentic-discovery:test              # Run test verification
```

---

### Deliverable Files Generated in Each Run (`runs/<run_id>/`)
* **`discovery_report.html`**: Responsive Claude-themed dashboard with tabs for Health Triage, Schema Profiles, 6-Dimension DQ Assertions, and Full Audit Trail.
* **`AUDIT_REPORT.md`**: Executive markdown report formatted for wikis.
* **`audit.jsonl`**: Immutable audit telemetry logging every decision, duration, and query.
* **`state.json`**: Checkpoint payload used for resumability and Q&A context.
