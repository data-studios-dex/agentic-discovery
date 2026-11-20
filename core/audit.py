"""
S5 - Comprehensive Audit Telemetry & Governance Logger.
Appends every gate decision, phase transition, agent action, SQL execution,
and compliance evaluation to `runs/<run_id>/audit.jsonl`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .schemas import GateDecision, utcnow


class Audit:
    def __init__(self, run_id: str, base_dir: Path):
        self.run_id = run_id
        self.run_dir = base_dir / "runs" / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.run_dir / "audit.jsonl"
        self._events: list[dict[str, Any]] = []

    def log(self, event_type: str, payload: dict[str, Any]) -> None:
        record = {
            "run_id": self.run_id,
            "event_type": event_type,
            "timestamp": utcnow(),
            **payload
        }
        self._events.append(record)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def gate(self, decision: GateDecision) -> None:
        self.log("gate_decision", decision.to_dict())

    def agent_action(self, agent: str, action: str, details: dict[str, Any]) -> None:
        self.log("agent_lifecycle", {"agent": agent, "action": action, "details": details})

    def sql_executed(self, sql_id: str, table: str, sql: str, duration_ms: float, violations: int, error: Optional[str] = None) -> None:
        self.log("sql_execution", {
            "sql_id": sql_id,
            "table": table,
            "sql": sql,
            "duration_ms": duration_ms,
            "violations": violations,
            "status": "success" if not error else "failed",
            "error": error
        })

    def note(self, message: str, level: str = "INFO", **kwargs) -> None:
        self.log("note", {"message": message, "level": level, **kwargs})

    def get_events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def summary(self) -> dict[str, Any]:
        """Provides high-level audit metrics for executive presentation."""
        gates = [e for e in self._events if e["event_type"] == "gate_decision"]
        sqls = [e for e in self._events if e["event_type"] == "sql_execution"]
        return {
            "total_events": len(self._events),
            "gate_decisions": len(gates),
            "sql_queries_executed": len(sqls),
            "total_violations_found": sum(s.get("violations", 0) for s in sqls),
            "audit_file": str(self.log_file)
        }
