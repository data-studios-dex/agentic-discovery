"""
S7 - Session State Checkpointing & Resumability.
Persists pipeline state to `runs/<run_id>/state.json` on every gate transition.
Supports `--resume` to recover an interrupted pipeline run.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .schemas import (
    DQRule,
    SchemaManifest,
    SQLItem,
    TableHealthTriage,
    utcnow,
)


class StateManager:
    def __init__(self, run_id: str, base_dir: Path):
        self.run_id = run_id
        self.run_dir = base_dir / "runs" / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.run_dir / "state.json"

    def checkpoint(self,
                   current_gate: str,
                   manifest: Optional[SchemaManifest] = None,
                   profiling_items: Optional[list[SQLItem]] = None,
                   rules: Optional[list[DQRule]] = None,
                   triages: Optional[list[TableHealthTriage]] = None,
                   reports: Optional[dict[str, str]] = None) -> None:
        payload = {
            "run_id": self.run_id,
            "last_gate": current_gate,
            "timestamp": utcnow(),
            "manifest": manifest.to_dict() if manifest else None,
            "profiling_count": len(profiling_items or []),
            "dq_rules_count": len(rules or []),
            "triages": [t.to_dict() for t in (triages or [])],
            "reports": reports or {}
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)

    def load(self) -> Optional[dict[str, Any]]:
        if not self.state_file.exists():
            return None
        with open(self.state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def find_latest_run(cls, base_dir: Path) -> Optional[str]:
        runs_dir = base_dir / "runs"
        if not runs_dir.exists():
            return None
        candidates = [p for p in runs_dir.iterdir() if p.is_dir() and (p / "state.json").exists()]
        if not candidates:
            return None
        latest = max(candidates, key=lambda p: (p / "state.json").stat().st_mtime)
        return latest.name
