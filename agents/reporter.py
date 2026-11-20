"""
Governance Reporter Subagent.
Compiles comprehensive auditing deliverables:
  * Full JSONL Audit Log (audit.jsonl)
  * Executive Markdown Audit Report (AUDIT_REPORT.md)
  * Claude-Themed Interactive HTML Governance Report (discovery_report.html)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from core.schemas import DQRule, SchemaManifest, SQLItem, TableHealthTriage
from .base import Agent


class ReporterAgent(Agent):
    name = "governance_reporter"
    skill_name = "governance_reporter"

    def compile_reports(self,
                        manifest: SchemaManifest,
                        profiling_items: list[SQLItem],
                        rules: list[DQRule],
                        triages: list[TableHealthTriage],
                        output_dir: Path) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        reports = {}

        # 1. Audit trail log file
        audit_path = output_dir / "audit.jsonl"
        reports["audit"] = str(audit_path)

        # 2. Markdown Audit Report
        md_path = output_dir / "AUDIT_REPORT.md"
        self._export_markdown(manifest, profiling_items, rules, triages, md_path)
        reports["markdown"] = str(md_path)

        # 3. Interactive Claude-Themed HTML Dashboard
        html_path = output_dir / "discovery_report.html"
        self._export_html(manifest, profiling_items, rules, triages, html_path)
        reports["html"] = str(html_path)

        self.audit.agent_action(self.name, "reports_compiled", {"exports": reports})
        return reports

    def _export_markdown(self,
                         manifest: SchemaManifest,
                         profiling_items: list[SQLItem],
                         rules: list[DQRule],
                         triages: list[TableHealthTriage],
                         path: Path) -> None:
        md = ["# 🛡️ Enterprise Database Discovery & Data Quality Audit Report\n"]
        md.append(f"**Run ID**: `{self.audit.run_id}` | **Dialect**: `{manifest.dialect.upper()}` | **Schema**: `{manifest.schema_name}`\n")
        md.append(f"**Database**: `{manifest.database_url_masked}`\n")

        # Summary KPIs
        total_tables = manifest.table_count
        total_rows = sum(t.row_count for t in manifest.tables)
        total_rules = len(rules)
        passed_rules = sum(1 for r in rules if r.passed)
        failed_rules = total_rules - passed_rules
        score = round((passed_rules / total_rules * 100.0) if total_rules > 0 else 100.0, 1)

        md.append("## Executive Health Summary\n")
        md.append(f"- **Overall Quality Score**: `{score}%` ({passed_rules}/{total_rules} assertions passed)")
        md.append(f"- **Tables Discovered**: `{total_tables}` | **Total Rows**: `{total_rows:,}`")
        md.append(f"- **Total Violations Detected**: `{failed_rules}`\n")

        md.append("### Table Health Triage\n")
        md.append("| Table Name | Health Status | Quality Score | Checks Passed | Violations | Notes / Defects |")
        md.append("|---|---|---|---|---|---|")
        for tr in triages:
            reasons_str = "; ".join(tr.reasons) if tr.reasons else "Clean"
            md.append(f"| `{tr.table_name}` | **{tr.health}** | {tr.score}% | {tr.passed_dq_checks}/{tr.total_dq_checks} | {tr.failed_dq_checks} | {reasons_str} |")
        md.append("\n---\n")

        # Discovered Schema Structure
        md.append("## Discovered Schema Architecture\n")
        for t in manifest.tables:
            md.append(f"### Table: `{t.table_name}` ({t.row_count:,} rows)")
            md.append(f"- **Primary Keys**: `{', '.join(t.primary_keys) or 'None'}`\n")
            md.append("| Column | Data Type | Nullable | Primary Key |")
            md.append("|---|---|---|---|")
            for c in t.columns:
                md.append(f"| `{c.column_name}` | `{c.data_type}` | {'YES' if c.is_nullable else 'NO'} | {'YES' if c.is_primary_key else 'NO'} |")
            md.append("\n")

        # DQ Assertions
        md.append("## Evaluated Data Quality Assertions\n")
        md.append("| Rule ID | Table | Dimension | Severity | Assertion | Violations | Status |")
        md.append("|---|---|---|---|---|---|---|")
        for r in rules:
            status = "PASSED" if r.passed else "FAILED"
            md.append(f"| `{r.rule_id}` | `{r.table_name}` | {r.dimension} | {r.severity} | {r.assertion} | {r.check_sql.violation_count} | **{status}** |")

        path.write_text("\n".join(md), encoding="utf-8")

    def _export_html(self,
                     manifest: SchemaManifest,
                     profiling_items: list[SQLItem],
                     rules: list[DQRule],
                     triages: list[TableHealthTriage],
                     path: Path) -> None:
        total_tables = manifest.table_count
        total_rows = sum(t.row_count for t in manifest.tables)
        total_rules = len(rules)
        passed_rules = sum(1 for r in rules if r.passed)
        failed_rules = total_rules - passed_rules
        overall_score = round((passed_rules / total_rules * 100.0) if total_rules > 0 else 100.0, 1)

        events = self.audit.get_events()
        gate_events = [e for e in events if e.get("event_type") == "gate_decision"]

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise Database Discovery & DQ Audit | Run {self.audit.run_id}</title>
    <style>
        :root {{
            --bg-primary: #191816;
            --bg-secondary: #22211E;
            --bg-card: #2B2A26;
            --bg-hover: #35342F;
            --border-color: #3D3C36;
            --border-subtle: #2E2D28;
            --text-primary: #ECE8E1;
            --text-secondary: #A8A49C;
            --text-muted: #78756E;
            --accent-terracotta: #D97746;
            --accent-terracotta-hover: #E68858;
            --accent-warm-amber: #DDA15E;
            --accent-soft-green: #609966;
            --badge-healthy-bg: rgba(96, 153, 102, 0.2);
            --badge-healthy-text: #9DC08B;
            --badge-warning-bg: rgba(221, 161, 94, 0.2);
            --badge-warning-text: #F4D06F;
            --badge-degraded-bg: rgba(217, 83, 79, 0.2);
            --badge-degraded-text: #E57373;
            --font-serif: "Copernicus", "Tiempos Headline", "Iowan Old Style", Georgia, serif;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            --font-mono: "JetBrains Mono", "Fira Code", Menlo, monospace;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: var(--font-sans);
            line-height: 1.5;
            padding: 32px 48px;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}

        .brand h1 {{
            font-family: var(--font-serif);
            font-size: 28px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 6px;
            letter-spacing: -0.02em;
        }}

        .brand p {{ color: var(--text-secondary); font-size: 14px; }}

        .conn-pill {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 6px 16px;
            font-size: 13px;
        }}

        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 18px;
            margin-bottom: 32px;
        }}

        .kpi-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            border-left: 4px solid var(--accent-terracotta);
        }}

        .kpi-card h4 {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}

        .kpi-card .val {{
            font-size: 32px;
            font-weight: 700;
            font-family: var(--font-serif);
            color: var(--text-primary);
        }}

        .kpi-card .sub {{ font-size: 12px; color: var(--text-secondary); margin-top: 4px; }}

        /* Tabs */
        .tabs {{
            display: flex;
            gap: 8px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 28px;
        }}

        .tab-btn {{
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 15px;
            font-weight: 500;
            padding: 10px 20px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s ease;
        }}

        .tab-btn:hover {{ color: var(--text-primary); }}
        .tab-btn.active {{
            color: var(--accent-terracotta);
            border-bottom: 2px solid var(--accent-terracotta);
        }}

        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}

        /* Tables */
        .table-wrapper {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 32px;
        }}

        .table-header {{
            padding: 16px 20px;
            background: var(--bg-card);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .table-header h3 {{
            font-family: var(--font-serif);
            font-size: 18px;
            color: var(--text-primary);
        }}

        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}

        th {{
            background: var(--bg-card);
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.05em;
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}

        td {{
            padding: 14px 16px;
            border-bottom: 1px solid var(--border-subtle);
            color: var(--text-primary);
            vertical-align: top;
        }}

        tr:hover td {{ background: var(--bg-hover); }}

        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .badge-healthy {{ background: var(--badge-healthy-bg); color: var(--badge-healthy-text); }}
        .badge-needs_attention {{ background: var(--badge-warning-bg); color: var(--badge-warning-text); }}
        .badge-degraded {{ background: var(--badge-degraded-bg); color: var(--badge-degraded-text); }}

        code {{
            font-family: var(--font-mono);
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border-subtle);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
            color: var(--accent-terracotta-hover);
        }}

        .search-box {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 13px;
            min-width: 260px;
            outline: none;
            margin-bottom: 16px;
        }}
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <h1>🛡️ Enterprise Database Discovery & Governance</h1>
            <p>Autonomous Profiling, 6-Dimension Quality Auditing & Step Enforcement (S1-S7)</p>
        </div>
        <div class="conn-pill">
            <span>Run: <code>{self.audit.run_id}</code></span> |
            <span>Database: <b>{manifest.dialect.upper()}</b></span> |
            <span>Schema: <code>{manifest.schema_name}</code></span>
        </div>
    </header>

    <div class="kpi-grid">
        <div class="kpi-card">
            <h4>Overall Quality Score</h4>
            <div class="val">{overall_score}%</div>
            <div class="sub">{passed_rules} of {total_rules} checks passed</div>
        </div>
        <div class="kpi-card">
            <h4>Discovered Tables</h4>
            <div class="val">{total_tables}</div>
            <div class="sub">{total_rows:,} total rows profiled</div>
        </div>
        <div class="kpi-card">
            <h4>Quality Violations</h4>
            <div class="val">{failed_rules}</div>
            <div class="sub">Detected data anomalies</div>
        </div>
        <div class="kpi-card">
            <h4>Audit Records</h4>
            <div class="val">{len(events)}</div>
            <div class="sub">Immutable audit entries</div>
        </div>
    </div>

    <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('tab-triage')">📊 Table Health Triage</button>
        <button class="tab-btn" onclick="switchTab('tab-schema')">📋 Discovered Schemas</button>
        <button class="tab-btn" onclick="switchTab('tab-dq')">🛡️ DQ Assertions & Defects</button>
        <button class="tab-btn" onclick="switchTab('tab-audit')">🔍 Full Audit Trail (S5)</button>
    </div>

    <!-- TAB 1: Health Triage -->
    <div id="tab-triage" class="tab-content active">
        <div class="table-wrapper">
            <div class="table-header">
                <h3>Table Health Scoring & Defect Triage</h3>
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 20%;">Table Name</th>
                        <th style="width: 15%;">Health Status</th>
                        <th style="width: 15%;">Quality Score</th>
                        <th style="width: 15%;">Passed / Total Checks</th>
                        <th style="width: 35%;">Health Diagnostics & Reasons</th>
                    </tr>
                </thead>
                <tbody>
"""
        for tr in triages:
            badge_cls = f"badge-{tr.health.lower()}"
            reasons_html = "<br>".join(f"• {r}" for r in tr.reasons)
            html += f"""
                    <tr>
                        <td><b>{tr.table_name}</b></td>
                        <td><span class="badge {badge_cls}">{tr.health}</span></td>
                        <td><b>{tr.score}%</b></td>
                        <td>{tr.passed_dq_checks} / {tr.total_dq_checks}</td>
                        <td><small>{reasons_html}</small></td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
    </div>

    <!-- TAB 2: Schema Discovery -->
    <div id="tab-schema" class="tab-content">
"""
        for t in manifest.tables:
            html += f"""
        <div class="table-wrapper">
            <div class="table-header">
                <h3>Table: <code>{t.table_name}</code> ({t.row_count:,} rows)</h3>
                <span style="font-size: 12px; color: var(--text-secondary);">PK: {', '.join(t.primary_keys) or 'None'}</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Column Name</th>
                        <th>Data Type</th>
                        <th>Nullability</th>
                        <th>Primary Key</th>
                    </tr>
                </thead>
                <tbody>
"""
            for col in t.columns:
                html += f"""
                    <tr>
                        <td><b>{col.column_name}</b></td>
                        <td><code>{col.data_type}</code></td>
                        <td>{'Nullable' if col.is_nullable else '<b style="color: var(--accent-terracotta);">NOT NULL</b>'}</td>
                        <td>{'✔ YES' if col.is_primary_key else '—'}</td>
                    </tr>
"""
            html += """
                </tbody>
            </table>
        </div>
"""
        html += """
    </div>

    <!-- TAB 3: DQ Rules -->
    <div id="tab-dq" class="tab-content">
        <div class="table-wrapper">
            <div class="table-header">
                <h3>6-Dimension Data Quality Rule Evaluations</h3>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Rule ID</th>
                        <th>Table</th>
                        <th>Dimension</th>
                        <th>Severity</th>
                        <th>Assertion Description</th>
                        <th>Violations</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
"""
        for r in rules:
            status_cls = "badge-healthy" if r.passed else "badge-degraded"
            status_text = "PASSED" if r.passed else "FAILED"
            html += f"""
                    <tr>
                        <td><code>{r.rule_id}</code></td>
                        <td><b>{r.table_name}</b></td>
                        <td><span class="badge" style="background: rgba(221,161,94,0.15); color: var(--accent-warm-amber);">{r.dimension}</span></td>
                        <td>{r.severity}</td>
                        <td>{r.assertion}</td>
                        <td><b>{r.check_sql.violation_count}</b></td>
                        <td><span class="badge {status_cls}">{status_text}</span></td>
                    </tr>
"""
        html += f"""
                </tbody>
            </table>
        </div>
    </div>

    <!-- TAB 4: Full Audit Trail -->
    <div id="tab-audit" class="tab-content">
        <div class="table-wrapper">
            <div class="table-header">
                <h3>Quality Gates G1-G6 Step Enforcement (S4)</h3>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Gate</th>
                        <th>State</th>
                        <th>Evaluation Decision & Reason</th>
                        <th>Timestamp (UTC)</th>
                    </tr>
                </thead>
                <tbody>
"""
        for g in gate_events:
            gate_id = g.get("gate_id", "GATE")
            state = g.get("state", "open")
            reason = g.get("reason", "")
            ts = g.get("timestamp", "")
            state_cls = "badge-healthy" if state == "open" else "badge-degraded"
            html += f"""
                    <tr>
                        <td><b>{gate_id}</b></td>
                        <td><span class="badge {state_cls}">{state.upper()}</span></td>
                        <td>{reason}</td>
                        <td><small>{ts}</small></td>
                    </tr>
"""
        html += f"""
                </tbody>
            </table>
        </div>

        <div class="table-wrapper">
            <div class="table-header">
                <h3>Immutable Telemetry & Execution Events Log</h3>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Event Type</th>
                        <th>Event Payload Details</th>
                    </tr>
                </thead>
                <tbody>
"""
        for e in events[-25:]:  # show recent 25 events
            html += f"""
                    <tr>
                        <td><small>{e.get('timestamp')}</small></td>
                        <td><code>{e.get('event_type')}</code></td>
                        <td><small style="color: var(--text-secondary);">{json.dumps({k: v for k, v in e.items() if k not in ('timestamp', 'event_type', 'run_id')})}</small></td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }
    </script>
</body>
</html>
"""
        path.write_text(html, encoding="utf-8")
