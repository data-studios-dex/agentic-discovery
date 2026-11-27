"""
Natural Language Q&A Engine for agentic-discovery.
Allows users to ask arbitrary natural language questions about schema structure,
profiling metrics, data quality defects, health triage, and root-cause analysis
after or during pipeline execution.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Optional

from .llm import LLM
from .state import StateManager


class DiscoveryQAEngine:
    def __init__(self, base_dir: Path, run_id: Optional[str] = None, llm: Optional[LLM] = None):
        self.base_dir = base_dir
        self.run_id = run_id or StateManager.find_latest_run(base_dir)
        self.llm = llm or LLM()
        self.state_data: dict[str, Any] = {}
        self.audit_events: list[dict[str, Any]] = []
        self._load_run_context()

    def _load_run_context(self) -> None:
        if not self.run_id:
            return
        state_mgr = StateManager(self.run_id, self.base_dir)
        self.state_data = state_mgr.load() or {}

        audit_file = self.base_dir / "runs" / self.run_id / "audit.jsonl"
        if audit_file.exists():
            for line in audit_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        self.audit_events.append(json.loads(line))
                    except Exception:
                        pass

    def answer_question(self, question: str) -> str:
        """Answers a user's natural language question based on the latest run telemetry."""
        if not self.run_id or not self.state_data:
            from .state import StateManager
            available = [r["run_id"] for r in StateManager.list_runs(self.base_dir)]
            avail_str = f" Available runs: {', '.join(available)}" if available else " No runs recorded yet."
            return f"Run ID '{self.run_id}' was not found or has no state.json.{avail_str}\nPlease check the Run ID or run discovery first via `python run.py start`."

        # If LLM is available in api or managed mode, use Claude reasoning
        if self.llm.mode in ("api", "managed"):
            context_summary = json.dumps(self.state_data, indent=2)
            prompt = f"""
You are an expert Data Governance and Database Auditor analyzing the results of a database discovery and quality run.
User Question: {question}

Run Context:
Run ID: {self.run_id}
State Payload:
{context_summary}

Please provide a clear, concise, actionable answer citing specific tables, columns, violation counts, and health statuses where relevant.
""".strip()
            resp = self.llm.call(prompt)
            if resp:
                return resp

        # Offline deterministic NLP response engine
        return self._deterministic_answer(question)

    def _deterministic_answer(self, q: str) -> str:
        q_low = q.lower().strip()
        manifest = self.state_data.get("manifest") or {}
        tables = manifest.get("tables", [])
        triages = self.state_data.get("triages", [])
        reports = self.state_data.get("reports", {})

        # Identify if a specific table is mentioned
        matched_table = None
        matched_triage = None
        for t in tables:
            t_name = t.get("table_name", "").lower()
            if t_name and re.search(rf"\b{re.escape(t_name)}\b", q_low):
                matched_table = t
                break
        if not matched_table:
            for t in tables:
                t_name = t.get("table_name", "").lower()
                if t_name and t_name in q_low:
                    matched_table = t
                    break

        if matched_table:
            for tr in triages:
                if tr.get("table_name") == matched_table.get("table_name"):
                    matched_triage = tr
                    break

        # 1. Remediation / How to fix questions
        if any(k in q_low for k in ("fix", "remediate", "remediation", "how to solve", "action", "recommend")):
            if matched_triage:
                reasons = matched_triage.get("reasons", [])
                t_name = matched_triage.get("table_name")
                fixes = []
                for r in reasons:
                    if "email" in r.lower():
                        fixes.append(f"-- Fix invalid email format in {t_name}:\nUPDATE {t_name} SET email = 'unknown@domain.com' WHERE email NOT LIKE '%@%.%';")
                    elif "monetary" in r.lower() or "negative" in r.lower():
                        fixes.append(f"-- Correct negative monetary amounts in {t_name}:\nUPDATE {t_name} SET total_amount = ABS(total_amount) WHERE total_amount < 0;")
                    elif "null" in r.lower():
                        fixes.append(f"-- Fill or flag missing null values in {t_name}:\nUPDATE {t_name} SET ... = DEFAULT WHERE ... IS NULL;")
                    else:
                        fixes.append(f"-- Investigate defect: {r}")
                if fixes:
                    return f"### Recommended SQL Remediation for Table `{t_name}`\n\n```sql\n" + "\n\n".join(fixes) + "\n```"
                return f"Table `{t_name}` has no active defects requiring remediation."

            # General remediation
            all_reasons = []
            for tr in triages:
                for r in tr.get("reasons", []):
                    if "violations" in r:
                        all_reasons.append(f"- **`{tr.get('table_name')}`**: {r}")
            if all_reasons:
                return (
                    f"### Recommended Actions for Detected Defects (Run `{self.run_id}`)\n"
                    + "\n".join(all_reasons)
                    + "\n\n*To see SQL remediation scripts for a specific table, ask: `How to fix table <name>?`*"
                )
            return "No data quality violations detected across any tables. All checks are clean!"

        # 2. Specific Table Structure / Describe / Columns
        if matched_table and any(k in q_low for k in ("column", "type", "structure", "schema", "describe", "detail", "datatype")):
            cols = matched_table.get("columns", [])
            col_lines = []
            for c in cols:
                pk_flag = " [PK]" if c.get("is_primary_key") else ""
                null_flag = "NULL" if c.get("is_nullable") else "NOT NULL"
                col_lines.append(f"- `{c['column_name']}` ({c['data_type']}{pk_flag}, {null_flag})")
            return (
                f"### Table Schema Architecture: `{matched_table.get('table_name')}`\n"
                f"- **Row Count**: `{matched_table.get('row_count', 0):,}`\n"
                f"- **Primary Keys**: `{', '.join(matched_table.get('primary_keys', [])) or 'None'}`\n"
                f"- **Columns ({len(cols)})**:\n"
                + "\n".join(col_lines)
            )

        # 3. Violations / Defects / Failures
        if any(k in q_low for k in ("violation", "defect", "fail", "broken", "bad data", "error")):
            if matched_triage:
                reasons = matched_triage.get("reasons", [])
                return (
                    f"### Violations & Defects in Table `{matched_triage.get('table_name')}`\n"
                    f"- **Health Status**: `{matched_triage.get('health')}`\n"
                    f"- **Checks Failed**: {matched_triage.get('failed_dq_checks')} / {matched_triage.get('total_dq_checks')}\n"
                    f"- **Violations**:\n"
                    + "\n".join(f"  • {r}" for r in reasons)
                )

            # All violations across database
            viol_list = []
            for tr in triages:
                if tr.get("failed_dq_checks", 0) > 0:
                    for r in tr.get("reasons", []):
                        viol_list.append(f"- **`{tr.get('table_name')}`**: {r}")
            if viol_list:
                return (
                    f"### Data Quality Violations Detected (Run `{self.run_id}`)\n"
                    + "\n".join(viol_list)
                    + f"\n\n*Total violating tables: {sum(1 for t in triages if t.get('failed_dq_checks', 0) > 0)} out of {len(triages)}.*"
                )
            return "No data quality violations detected! All evaluated rules passed successfully."

        # 4. Health / Degraded / Triage questions
        if any(k in q_low for k in ("why", "degraded", "health", "score", "status", "triage", "attention")):
            if matched_triage:
                reasons = matched_triage.get("reasons", [])
                return (
                    f"### Health Analysis for Table `{matched_triage.get('table_name')}`\n"
                    f"- **Status**: `{matched_triage.get('health')}` (Score: {matched_triage.get('score')} / 100%)\n"
                    f"- **Checks Passed**: {matched_triage.get('passed_dq_checks')} / {matched_triage.get('total_dq_checks')}\n"
                    f"- **Identified Reasons & Defects**:\n"
                    + "\n".join(f"  • {r}" for r in reasons)
                )

            # General health summary
            rows = []
            for tr in triages:
                h = tr.get("health")
                emoji = "🟢" if h == "HEALTHY" else "🟡" if h == "NEEDS_ATTENTION" else "🔴"
                rows.append(f"- {emoji} `{tr.get('table_name')}`: **{h}** (Score: {tr.get('score')}%, Passed: {tr.get('passed_dq_checks')}/{tr.get('total_dq_checks')})")
            return (
                f"### Overall Table Health Triage (Run `{self.run_id}`)\n"
                + "\n".join(rows)
                + f"\n\n*Ask: `Why is table <name> degraded?` to inspect defect details.*"
            )

        # 5. List Tables / Show Tables
        if any(k in q_low for k in ("what tables", "list table", "show table", "all table", "tables")):
            table_summary = []
            for t in tables:
                t_name = t.get("table_name")
                tr = next((x for x in triages if x.get("table_name") == t_name), {})
                h = tr.get("health", "UNKNOWN")
                table_summary.append(f"- `{t_name}`: {t.get('row_count', 0):,} rows | {len(t.get('columns', []))} columns | Status: `{h}`")
            return (
                f"### Discovered Tables ({len(tables)} tables in schema `{manifest.get('schema_name', 'main')}`)\n"
                + "\n".join(table_summary)
            )

        # 6. Row count / volume questions
        if any(k in q_low for k in ("row", "count", "volume", "how many rows", "size")):
            if matched_table:
                return f"Table `{matched_table.get('table_name')}` contains `{matched_table.get('row_count', 0):,}` rows and `{len(matched_table.get('columns', []))}` columns."
            total_rows = sum(t.get("row_count", 0) for t in tables)
            table_breakdown = "\n".join(f"- `{t['table_name']}`: {t.get('row_count', 0):,} rows" for t in tables)
            return (
                f"### Database Volume Summary\n"
                f"- **Total Discovered Rows**: `{total_rows:,}` rows across `{len(tables)}` tables.\n"
                f"**Breakdown by Table**:\n{table_breakdown}"
            )

        # 7. Primary Key & Uniqueness questions
        if any(k in q_low for k in ("pk", "primary key", "unique", "duplicate")):
            pks = []
            for t in tables:
                pk_list = t.get("primary_keys", [])
                pks.append(f"- `{t['table_name']}`: {', '.join(pk_list) if pk_list else 'No primary key defined'}")
            return (
                f"### Primary Key & Uniqueness Architecture\n"
                f"{chr(10).join(pks)}"
            )

        # 8. Null & Missingness questions
        if any(k in q_low for k in ("null", "missing", "completeness")):
            not_null_cols = []
            for t in tables:
                for c in t.get("columns", []):
                    if not c.get("is_nullable"):
                        not_null_cols.append(f"- `{t['table_name']}.{c['column_name']}` (Declared NOT NULL)")
            return (
                f"### Mandatory NOT NULL Columns Enforced\n"
                f"{chr(10).join(not_null_cols[:10])}\n"
                f"*(Showing top mandatory attributes audited for completeness)*"
            )

        # 9. Report location questions
        if any(k in q_low for k in ("where", "report", "file", "saved", "html", "path")):
            html_rep = reports.get("html", f"runs/{self.run_id}/discovery_report.html")
            md_rep = reports.get("markdown", f"runs/{self.run_id}/AUDIT_REPORT.md")
            audit_rep = reports.get("audit", f"runs/{self.run_id}/audit.jsonl")
            return (
                f"### Deliverable File Locations (Run `{self.run_id}`)\n"
                f"- **Interactive HTML Dashboard**: `{html_rep}`\n"
                f"- **Executive Markdown Summary**: `{md_rep}`\n"
                f"- **Full Audit Trail**: `{audit_rep}`"
            )

        # Default fallback summary
        return (
            f"### Run Summary (`{self.run_id}`)\n"
            f"- **Database Engine**: `{manifest.get('dialect', 'N/A').upper()}` | **Schema**: `{manifest.get('schema_name', 'main')}`\n"
            f"- **Tables Profiled**: `{len(tables)}`\n"
            f"- **Interactive Dashboard**: `{reports.get('html', 'N/A')}`\n\n"
            f"You can ask natural language questions such as:\n"
            f"  • *'Show all data quality violations'* \n"
            f"  • *'Why is table orders marked NEEDS_ATTENTION?'*\n"
            f"  • *'How to fix defects in table customers?'*\n"
            f"  • *'Show structure and columns of table products'*\n"
            f"  • *'What is the total row count across all tables?'*\n"
            f"  • *'Where is the HTML dashboard saved?'*"
        )
