"""
S2 - Master Hub-and-Spoke Orchestrator for Database Discovery & Quality Governance.
Coordinates subagents across sessions S1-S7, enforces unbypassable gates G1-G6,
manages session state checkpoints, and runs S1 self-healing execution loops.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import Callable, Optional

from core.audit import Audit
from core.db import DB
from core.gates import (
    Gate,
    g1_discovery,
    g2_profile_sql,
    g3_profile_execute,
    g4_dq_rules,
    g5_health_review,
    g6_governance_export,
)
from core.llm import LLM
from core.loop import AgenticLoop
from core.schemas import DQRule, SQLItem, TableHealthTriage
from core.state import StateManager

from agents.discovery import DiscoveryAgent
from agents.profile_sqlgen import SQLProfilerAgent
from agents.dq_rulegen import DQRuleGenAgent
from agents.sql_validator import SQLValidatorAgent
from agents.query_fixer import QueryFixerAgent
from agents.reviewer import ReviewerAgent
from agents.reporter import ReporterAgent


class DiscoveryOrchestrator:
    def __init__(self,
                 db_url: str,
                 base_dir: Path,
                 run_id: Optional[str] = None,
                 llm_mode: Optional[str] = None,
                 model: Optional[str] = None):
        self.base_dir = base_dir
        self.run_id = run_id or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.audit = Audit(self.run_id, self.base_dir)
        self.state = StateManager(self.run_id, self.base_dir)
        self.db = DB(db_url)
        self.llm = LLM(mode=llm_mode, model=model, audit=self.audit, run_id=self.run_id)
        self.loop = AgenticLoop(self.audit)

        # Subagents (S2 Spokes)
        self.discovery_agent = DiscoveryAgent(self.db, self.llm, self.audit)
        self.profiler_agent = SQLProfilerAgent(self.db, self.llm, self.audit)
        self.dq_rulegen_agent = DQRuleGenAgent(self.db, self.llm, self.audit)
        self.validator_agent = SQLValidatorAgent(self.db, self.llm, self.audit)
        self.fixer_agent = QueryFixerAgent(self.db, self.llm, self.audit)
        self.reviewer_agent = ReviewerAgent(self.db, self.llm, self.audit)
        self.reporter_agent = ReporterAgent(self.db, self.llm, self.audit)

        # Quality Gates (S4)
        self.gate_g1 = Gate("G1_DISCOVERY", g1_discovery)
        self.gate_g2 = Gate("G2_PROFILE_SQL", g2_profile_sql)
        self.gate_g3 = Gate("G3_PROFILE_EXECUTE", g3_profile_execute)
        self.gate_g4 = Gate("G4_DQ_RULES", g4_dq_rules)
        self.gate_g5 = Gate("G5_HEALTH_REVIEW", g5_health_review)
        self.gate_g6 = Gate("G6_GOVERNANCE_EXPORT", g6_governance_export)

    def run_pipeline(self,
                     schema_name: str = "main",
                     target_tables: Optional[list[str]] = None,
                     mode: str = "both",
                     progress_callback: Optional[Callable[[str, str], None]] = None) -> dict[str, str]:
        """
        Executes end-to-end autonomous discovery, profiling, and DQ auditing pipeline.
        Modes: 'profiling', 'checks', 'both'
        """
        def notify(phase: str, msg: str):
            if progress_callback:
                progress_callback(phase, msg)

        self.audit.note(
            f"Starting Discovery Orchestration Pipeline run {self.run_id}",
            dialect=self.db.dialect,
            schema=schema_name,
            mode=mode
        )

        # ---------------- Phase 1: Introspect & Discover (G1) --------------
        notify("PHASE 1/6", f"Introspecting schema '{schema_name}' on {self.db.dialect_label} database")
        manifest = self.discovery_agent.introspect(schema_name, target_tables)
        dec_g1 = self.gate_g1.enforce(self.audit, manifest=manifest)
        notify("GATE G1 [OPEN]", dec_g1.reason)
        self.state.checkpoint("G1_OPEN", manifest=manifest)

        # ---------------- Phase 2: Formulate Profiling SQL (G2) ------------
        notify("PHASE 2/6", "Formulating statistical profiling queries (volume, nulls, distincts)")
        profiling_items: list[SQLItem] = []
        for table in manifest.tables:
            profiling_items.extend(self.profiler_agent.formulate_profiling(table))

        dec_g2 = self.gate_g2.enforce(self.audit, profiling_items=profiling_items)
        notify("GATE G2 [OPEN]", dec_g2.reason)
        self.state.checkpoint("G2_OPEN", manifest=manifest, profiling_items=profiling_items)

        # ---------------- Phase 3: Execute Profiling with S1 Loop (G3) -----
        notify("PHASE 3/6", f"Executing {len(profiling_items)} profiling queries on {self.db.dialect_label}")
        for item in profiling_items:
            self.loop.run_query_with_healing(
                item=item,
                execute_fn=self.db.execute,
                validate_fn=self.validator_agent.validate,
                fix_fn=self.fixer_agent.repair_query
            )

        dec_g3 = self.gate_g3.enforce(self.audit, profiling_items=profiling_items)
        notify("GATE G3 [OPEN]", dec_g3.reason)
        self.state.checkpoint("G3_OPEN", manifest=manifest, profiling_items=profiling_items)

        if mode == "profiling":
            triages = [self.reviewer_agent.review_table_health(t, []) for t in manifest.tables]
            run_output_dir = self.base_dir / "runs" / self.run_id
            reports = self.reporter_agent.compile_reports(manifest, profiling_items, [], triages, run_output_dir)
            notify("GATE G6 [OPEN]", "Profiling deliverables exported successfully.")
            return reports

        # ---------------- Phase 4: DQ Rule Generation & Execution (G4) ----
        notify("PHASE 4/6", "Synthesizing 6-dimension DQ rules (Completeness, Uniqueness, Validity, Timeliness)")
        dq_rules: list[DQRule] = []
        for table in manifest.tables:
            dq_rules.extend(self.dq_rulegen_agent.generate_rules(table))

        # Execute DQ checks with S1 loop
        for rule in dq_rules:
            self.loop.run_query_with_healing(
                item=rule.check_sql,
                execute_fn=self.db.execute,
                validate_fn=self.validator_agent.validate,
                fix_fn=self.fixer_agent.repair_query
            )

        dec_g4 = self.gate_g4.enforce(self.audit, rules=dq_rules)
        notify("GATE G4 [OPEN]", dec_g4.reason)
        self.state.checkpoint("G4_OPEN", manifest=manifest, profiling_items=profiling_items, rules=dq_rules)

        # ---------------- Phase 5: Table Health Review & Triage (G5) -------
        notify("PHASE 5/6", "Triaging table health (HEALTHY, NEEDS_ATTENTION, DEGRADED)")
        triages: list[TableHealthTriage] = []
        for table in manifest.tables:
            triages.append(self.reviewer_agent.review_table_health(table, dq_rules))

        dec_g5 = self.gate_g5.enforce(self.audit, triages=triages)
        notify("GATE G5 [OPEN]", dec_g5.reason)
        self.state.checkpoint("G5_OPEN", manifest=manifest, profiling_items=profiling_items, rules=dq_rules, triages=triages)

        # ---------------- Phase 6: Governance Deliverables & Full Audit (G6)
        notify("PHASE 6/6", "Compiling full audit trail, Markdown report & interactive Claude-themed HTML dashboard")
        run_output_dir = self.base_dir / "runs" / self.run_id
        reports = self.reporter_agent.compile_reports(manifest, profiling_items, dq_rules, triages, run_output_dir)
        dec_g6 = self.gate_g6.enforce(self.audit, reports=reports)
        notify("GATE G6 [OPEN]", dec_g6.reason)

        self.state.checkpoint("G6_OPEN", manifest=manifest, profiling_items=profiling_items, rules=dq_rules, triages=triages, reports=reports)
        self.audit.note("Pipeline completed with all gates G1-G6 OPEN.", level="SUCCESS")
        return reports
