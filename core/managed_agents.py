"""
Claude Managed Agents Control Plane & Registry for agentic-discovery.
Maps agent skills to persisted, versioned Managed Agents tracked in `managed_agents.json`.
Supports drift checking, idempotent provisioning, and isolated session execution.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

from .schemas import utcnow
from .skills import SkillRegistry, Skill


ROOT_DIR = Path(__file__).resolve().parent.parent
REGISTRY_FILE = Path(os.getenv("MANAGED_AGENTS_REGISTRY", str(ROOT_DIR / "managed_agents.json")))
DEFAULT_MODEL = "claude-sonnet-5-5"
FRAMEWORK_TAG = "agentic_discovery"

MANAGED_SKILLS = [
    "discovery_orchestrator",
    "db_discovery",
    "sql_profiler",
    "dq_rulegen",
    "sql_validator_fixer",
    "governance_reviewer",
    "governance_reporter"
]


class ManagedAgentRegistry:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or REGISTRY_FILE
        self.data: dict[str, Any] = {
            "framework": FRAMEWORK_TAG,
            "updated_at": utcnow(),
            "agents": {}
        }
        self.load()

    def load(self) -> None:
        if self.file_path_exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                pass

    def file_path_exists(self) -> bool:
        return self.path.exists()

    def save(self) -> None:
        self.data["updated_at"] = utcnow()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    @property
    def ready(self) -> bool:
        return bool(self.data.get("agents"))

    def get_agent(self, skill_name: str) -> Optional[dict[str, Any]]:
        return self.data.get("agents", {}).get(skill_name)


def compute_skill_hash(skill: Skill) -> str:
    content = f"{skill.name}:{skill.version}:{skill.body}".encode("utf-8")
    return f"sha256:{hashlib.sha256(content).hexdigest()[:24]}"


def provision(dry_run: bool = False, model: str = DEFAULT_MODEL, registry_path: Optional[Path] = None) -> dict[str, Any]:
    """Provisions skills into managed_agents.json."""
    registry = ManagedAgentRegistry(registry_path)
    skills = SkillRegistry()

    plan = {}
    for skill_name in MANAGED_SKILLS:
        skill = skills.get(skill_name)
        if not skill:
            continue

        cfg_hash = compute_skill_hash(skill)
        existing = registry.get_agent(skill_name)

        if existing and existing.get("config_hash") == cfg_hash:
            plan[skill_name] = {"status": "unchanged", "agent_id": existing.get("agent_id")}
        else:
            agent_id = existing.get("agent_id") if existing else f"agent_{hashlib.md5(skill_name.encode()).hexdigest()[:16]}"
            ver = (existing.get("version", 0) + 1) if existing else 1
            plan[skill_name] = {
                "status": "update" if existing else "create",
                "skill": skill_name,
                "agent_id": agent_id,
                "version": ver,
                "model": model,
                "skill_version": skill.version,
                "config_hash": cfg_hash,
                "updated_at": utcnow()
            }
            if not dry_run:
                registry.data["agents"][skill_name] = plan[skill_name]

    if not dry_run:
        registry.save()

    return plan


def check_managed_agents(registry_path: Optional[Path] = None) -> tuple[bool, list[str]]:
    """Checks for drift between SKILL.md files and managed_agents.json."""
    registry = ManagedAgentRegistry(registry_path)
    skills = SkillRegistry()
    drifts = []

    for skill_name in MANAGED_SKILLS:
        skill = skills.get(skill_name)
        if not skill:
            drifts.append(f"Skill '{skill_name}' defined in MANAGED_SKILLS but missing in skills/ directory.")
            continue
        cfg_hash = compute_skill_hash(skill)
        entry = registry.get_agent(skill_name)
        if not entry:
            drifts.append(f"Skill '{skill_name}' has not been provisioned in managed_agents.json.")
        elif entry.get("config_hash") != cfg_hash:
            drifts.append(f"Skill '{skill_name}' has drifted from registry (hash mismatch).")

    return len(drifts) == 0, drifts


def ensure_managed_agents_provisioned(registry_path: Optional[Path] = None, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    """
    Auto-provisions managed agents directly if missing or unprovisioned.
    Ensures zero manual setup required on fresh checkout/run.
    """
    registry = ManagedAgentRegistry(registry_path)
    needs_provision = not registry.ready
    if not needs_provision:
        for skill_name in MANAGED_SKILLS:
            if not registry.get_agent(skill_name):
                needs_provision = True
                break

    if needs_provision:
        return provision(dry_run=False, model=model, registry_path=registry_path)
    return {}
