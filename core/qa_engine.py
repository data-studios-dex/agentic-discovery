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
            return "No previous pipeline runs found to analyze. Please run the discovery pipeline first via `python run.py start`."

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

        # 1. Health / Degraded / Defect questions
        if any(k in q_low for k in ("why", "degraded", "health", "failed", "defect", "attention", "issue", "problem")):
            # Check for specific table
            for t in triages:
                t_name = t.get("table_name", "").lower()
                if t_name in q_low:
                    reasons = t.get("reasons", [])
                    return (
                        f"### Health Analysis for Table `{t.get('table_name')}`\n"
                        f"- **Status**: `{t.get('health')}` (Score: {t.get('score')}%)\n"
                        f"- **Checks Passed**: {t.get('passed_dq_checks')} / {t.get('total_dq_checks')}\n"
                        f"- **Identified Reasons & Defects**:\n" +
                        "\n".join(f"  • {r}" for r in reasons)
                    )

            # General health summary
            degraded = [t for t in triages if t.get("health") == "DEGRADED"]
            warn = [t for t in triages if t.get("health") == "NEEDS_ATTENTION"]
            return (
                f"### Overall Table Health Summary (Run `{self.run_id}`)\n"
                f"- **Total Tables Triaged**: {len(triages)}\n"
                f"- **DEGRADED Tables**: {len(degraded)} ({', '.join(t['table_name'] for t in degraded) if degraded else 'None'})\n"
                f"- **NEEDS_ATTENTION Tables**: {len(warn)} ({', '.join(t['table_name'] for t in warn) if warn else 'None'})\n"
                f"- **HEALTHY Tables**: {len(triages) - len(degraded) - len(warn)}\n\n"
                f"For details on a specific table, ask e.g. *'Why is table orders DEGRADED?'*"
            )

        # 2. Row count / volume questions
        if any(k in q_low for k in ("row", "count", "total rows", "volume", "how many rows")):
            total_rows = sum(t.get("row_count", 0) for t in tables)
            table_breakdown = "\n".join(f"- `{t['table_name']}`: {t.get('row_count', 0):,} rows" for t in tables)
            return (
                f"### Database Volume Summary\n"
                f"- **Total Discovered Rows**: `{total_rows:,}` rows across `{len(tables)}` tables.\n"
                f"**Breakdown by Table**:\n{table_breakdown}"
            )

        # 3. Primary Key & Uniqueness questions
        if any(k in q_low for k in ("pk", "primary key", "unique", "duplicate")):
            pks = []
            for t in tables:
                pk_list = t.get("primary_keys", [])
                pks.append(f"- `{t['table_name']}`: {', '.join(pk_list) if pk_list else 'No primary key defined'}")
            return (
                f"### Primary Key & Uniqueness Architecture\n"
                f"{chr(10).join(pks)}"
            )

        # 4. Null & Missingness questions
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

        # 5. Report location questions
        if any(k in q_low for k in ("where", "report", "file", "saved", "html")):
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
            f"- **Database Dialect**: `{manifest.get('dialect', 'N/A').upper()}` | **Schema**: `{manifest.get('schema_name', 'main')}`\n"
            f"- **Tables Profiled**: `{len(tables)}`\n"
            f"- **Interactive Report**: `{reports.get('html', 'N/A')}`\n\n"
            f"You can ask questions like:\n"
            f"  • *'Why is table orders DEGRADED?'*\n"
            f"  • *'How many total rows were discovered?'*\n"
            f"  • *'What are the primary keys?'*\n"
            f"  • *'Where is the HTML report saved?'*"
        )
