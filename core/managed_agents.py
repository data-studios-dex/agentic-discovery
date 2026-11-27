"""
Claude Managed Agents Control Plane & Registry for agentic-discovery.
Maps agent skills to persisted, versioned Managed Agents tracked in `managed_agents.json`.
Enforces the enterprise naming convention: DA_CL_{UseCase}_{AgentName}
Example: DA_CL_LakeHouse_BronzeLayerAgent -> DA_CL_Discovery_DbDiscoveryAgent
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
USE_CASE = "Discovery"

# Enterprise Managed Agents Specification adhering to: DA_CL_{UseCase}_{AgentName}
MANAGED_AGENTS_SPEC = [
    {
        "skill": "discovery_orchestrator",
        "agent_name": f"DA_CL_{USE_CASE}_DiscoveryOrchestratorAgent",
        "description": "Master orchestrator for database discovery, profiling, and quality governance",
    },
    {
        "skill": "db_discovery",
        "agent_name": f"DA_CL_{USE_CASE}_DbDiscoveryAgent",
        "description": "Database schema introspection, table structures, and column discovery",
    },
    {
        "skill": "sql_profiler",
        "agent_name": f"DA_CL_{USE_CASE}_SqlProfilerAgent",
        "description": "Non-destructive statistical profiling query formulation (volume, nulls, distincts)",
    },
    {
        "skill": "sql_validator_fixer",
        "agent_name": f"DA_CL_{USE_CASE}_SqlValidatorFixerAgent",
        "description": "SQL query AST validation, security linting, and self-healing repair",
    },
    {
        "skill": "dq_rulegen",
        "agent_name": f"DA_CL_{USE_CASE}_DqRuleGenAgent",
        "description": "Synthesis of 6-dimension data quality rules (Completeness, Uniqueness, Validity, Timeliness)",
    },
    {
        "skill": "governance_reviewer",
        "agent_name": f"DA_CL_{USE_CASE}_GovernanceReviewerAgent",
        "description": "Table health triage (HEALTHY, NEEDS_ATTENTION, DEGRADED) and quality scoring",
    },
    {
        "skill": "governance_reporter",
        "agent_name": f"DA_CL_{USE_CASE}_GovernanceReporterAgent",
        "description": "Interactive HTML dashboard, Markdown executive report, and JSONL audit trail compilation",
    },
]

MANAGED_SKILLS = [spec["skill"] for spec in MANAGED_AGENTS_SPEC]
SKILL_TO_AGENT_NAME = {spec["skill"]: spec["agent_name"] for spec in MANAGED_AGENTS_SPEC}
AGENT_NAME_TO_SKILL = {spec["agent_name"]: spec["skill"] for spec in MANAGED_AGENTS_SPEC}


class ManagedAgentRegistry:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or REGISTRY_FILE
        self.data: dict[str, Any] = {
            "framework": FRAMEWORK_TAG,
            "use_case": USE_CASE,
            "naming_convention": "DA_CL_{UseCase}_{AgentName}",
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
        self.data["use_case"] = USE_CASE
        self.data["naming_convention"] = "DA_CL_{UseCase}_{AgentName}"
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    @property
    def ready(self) -> bool:
        return bool(self.data.get("agents"))

    def get_agent(self, identifier: str) -> Optional[dict[str, Any]]:
        agents = self.data.get("agents", {})
        # 1. Direct match by managed agent name (DA_CL_Discovery_DbDiscoveryAgent)
        if identifier in agents:
            return agents[identifier]
        # 2. Match by skill name (db_discovery -> DA_CL_Discovery_DbDiscoveryAgent)
        mapped_name = SKILL_TO_AGENT_NAME.get(identifier)
        if mapped_name and mapped_name in agents:
            return agents[mapped_name]
        # 3. Fallback scan by skill or agent_name field
        for name, entry in agents.items():
            if entry.get("skill") == identifier or entry.get("agent_name") == identifier or name == identifier:
                return entry
        return None


def compute_skill_hash(skill: Skill) -> str:
    content = f"{skill.name}:{skill.version}:{skill.body}".encode("utf-8")
    return f"sha256:{hashlib.sha256(content).hexdigest()[:24]}"


def provision(dry_run: bool = False, model: str = DEFAULT_MODEL, registry_path: Optional[Path] = None) -> dict[str, Any]:
    """Provisions skills into managed_agents.json adhering to DA_CL_{UseCase}_{AgentName} convention."""
    registry = ManagedAgentRegistry(registry_path)
    skills = SkillRegistry()

    plan = {}
    for spec in MANAGED_AGENTS_SPEC:
        skill_name = spec["skill"]
        agent_name = spec["agent_name"]
        skill = skills.get(skill_name)
        if not skill:
            continue

        cfg_hash = compute_skill_hash(skill)
        existing = registry.get_agent(agent_name)

        if existing and existing.get("config_hash") == cfg_hash:
            plan[agent_name] = {
                "status": "unchanged",
                "agent_name": agent_name,
                "skill": skill_name,
                "agent_id": existing.get("agent_id")
            }
        else:
            agent_id = existing.get("agent_id") if existing else f"agent_{hashlib.md5(agent_name.encode()).hexdigest()[:16]}"
            ver = (existing.get("version", 0) + 1) if existing else 1
            plan[agent_name] = {
                "status": "update" if existing else "create",
                "agent_name": agent_name,
                "skill": skill_name,
                "agent_id": agent_id,
                "version": ver,
                "model": model,
                "skill_version": skill.version,
                "config_hash": cfg_hash,
                "updated_at": utcnow()
            }
            if not dry_run:
                registry.data["agents"][agent_name] = plan[agent_name]

    if not dry_run:
        registry.data["framework"] = FRAMEWORK_TAG
        registry.data["use_case"] = USE_CASE
        registry.data["naming_convention"] = "DA_CL_{UseCase}_{AgentName}"
        registry.save()

    return plan


def check_managed_agents(registry_path: Optional[Path] = None) -> tuple[bool, list[str]]:
    """Checks for drift between SKILL.md files and managed_agents.json."""
    registry = ManagedAgentRegistry(registry_path)
    skills = SkillRegistry()
    drifts = []

    for spec in MANAGED_AGENTS_SPEC:
        skill_name = spec["skill"]
        agent_name = spec["agent_name"]
        skill = skills.get(skill_name)
        if not skill:
            drifts.append(f"Skill '{skill_name}' defined in MANAGED_AGENTS_SPEC but missing in skills/ directory.")
            continue
        cfg_hash = compute_skill_hash(skill)
        entry = registry.get_agent(agent_name)
        if not entry:
            drifts.append(f"Managed Agent '{agent_name}' ({skill_name}) has not been provisioned in managed_agents.json.")
        elif entry.get("config_hash") != cfg_hash:
            drifts.append(f"Managed Agent '{agent_name}' ({skill_name}) has drifted from registry (hash mismatch).")

    return len(drifts) == 0, drifts


def ensure_managed_agents_provisioned(registry_path: Optional[Path] = None, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    """
    Auto-provisions managed agents directly if missing or unprovisioned.
    Ensures zero manual setup required on fresh checkout/run.
    """
    registry = ManagedAgentRegistry(registry_path)
    needs_provision = not registry.ready
    if not needs_provision:
        for spec in MANAGED_AGENTS_SPEC:
            if not registry.get_agent(spec["agent_name"]):
                needs_provision = True
                break

    if needs_provision:
        return provision(dry_run=False, model=model, registry_path=registry_path)
    return {}
