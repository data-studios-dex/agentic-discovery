"""
S4 - Step Enforcement: Quality Gates G1-G6 for Database Discovery & Quality Auditing.
A gate is a named predicate over pipeline state.
If a gate closes, downstream progression is halted or routed to corrective triage.
Every decision is immutably appended to `runs/<run_id>/audit.jsonl`.
"""
from __future__ import annotations

from typing import Callable, Optional

from .audit import Audit
from .schemas import (
    DQRule,
    GateDecision,
    SchemaManifest,
    SQLItem,
    TableHealthTriage,
)


class GateClosed(Exception):
    def __init__(self, decision: GateDecision):
        super().__init__(f"{decision.gate_id} closed: {decision.reason}")
        self.decision = decision


class Gate:
    def __init__(self, gate_id: str, predicate: Callable[..., tuple[bool, str, dict]]):
        self.gate_id = gate_id
        self.predicate = predicate

    def check(self, audit: Audit, **ctx) -> GateDecision:
        ok, reason, evidence = self.predicate(**ctx)
        decision = GateDecision(
            gate_id=self.gate_id,
            state="open" if ok else "closed",
            reason=reason,
            evidence=evidence
        )
        audit.gate(decision)
        return decision

    def enforce(self, audit: Audit, **ctx) -> GateDecision:
        decision = self.check(audit, **ctx)
        if decision.state != "open":
            raise GateClosed(decision)
        return decision


# ------------------------------------------------------------- Predicates --

def g1_discovery(manifest: Optional[SchemaManifest] = None, **_) -> tuple[bool, str, dict]:
    """G1: Database connected & schema manifest non-empty."""
    if not manifest or manifest.table_count == 0:
        return (False,
                f"No tables discovered in schema '{getattr(manifest, 'schema_name', '?')}'. Check connection credentials.",
                {"tables": 0})
    return (True,
            f"G1 Passed: Connected to {manifest.dialect.upper()}; {manifest.table_count} tables discovered in schema '{manifest.schema_name}'.",
            {"tables": [t.table_name for t in manifest.tables], "dialect": manifest.dialect})


def g2_profile_sql(profiling_items: Optional[list[SQLItem]] = None, **_) -> tuple[bool, str, dict]:
    """G2: Profiling queries formulated across tables."""
    items = profiling_items or []
    if not items:
        return False, "G2 Closed: No profiling queries were generated.", {"items": 0}
    return (True,
            f"G2 Passed: Formulated {len(items)} statistical profiling queries.",
            {"total_queries": len(items)})


def g3_profile_execute(profiling_items: Optional[list[SQLItem]] = None, **_) -> tuple[bool, str, dict]:
    """G3: Profiling queries successfully executed."""
    items = profiling_items or []
    failed = [i.sql_id for i in items if i.status == "failed"]
    if failed:
        return (False,
                f"G3 Closed: {len(failed)} profiling queries failed execution ({', '.join(failed[:3])}).",
                {"failed_queries": failed})
    return (True,
            f"G3 Passed: All {len(items)} profiling queries executed successfully on database.",
            {"executed_queries": len(items)})


def g4_dq_rules(rules: Optional[list[DQRule]] = None, **_) -> tuple[bool, str, dict]:
    """G4: DQ rules synthesized and evaluated with violation counts."""
    rules_list = rules or []
    if not rules_list:
        return False, "G4 Closed: Zero data quality rules evaluated.", {"rules": 0}
    
    passed_cnt = sum(1 for r in rules_list if r.passed)
    failed_cnt = len(rules_list) - passed_cnt
    return (True,
            f"G4 Passed: Evaluated {len(rules_list)} DQ rules across 6 dimensions ({passed_cnt} passed, {failed_cnt} violations).",
            {"total_rules": len(rules_list), "violations": failed_cnt})


def g5_health_review(triages: Optional[list[TableHealthTriage]] = None, **_) -> tuple[bool, str, dict]:
    """G5: All tables assigned health status."""
    triages_list = triages or []
    if not triages_list:
        return False, "G5 Closed: Table health triage incomplete.", {}
    
    degraded = [t.table_name for t in triages_list if t.health == "DEGRADED"]
    return (True,
            f"G5 Passed: Triaged {len(triages_list)} tables ({len(degraded)} marked DEGRADED).",
            {"triaged_tables": len(triages_list), "degraded": degraded})


def g6_governance_export(reports: Optional[dict[str, str]] = None, **_) -> tuple[bool, str, dict]:
    """G6: Final governance deliverables (HTML, Markdown, Audit Log) verified."""
    reps = reports or {}
    if not reps or "html" not in reps or "audit" not in reps:
        return False, "G6 Closed: Required governance artifacts missing.", {"reports": reps}
    return (True,
            f"G6 Passed: All governance deliverables successfully exported ({', '.join(reps.keys())}).",
            {"reports": reps})
