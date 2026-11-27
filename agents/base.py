"""Base Agent class for agentic-discovery subagents."""
from __future__ import annotations

from core.audit import Audit
from core.db import DB
from core.llm import LLM


class Agent:
    name = "agent"
    managed_agent_name = "DA_CL_Discovery_Agent"
    skill_name = ""

    def __init__(self, db: DB, llm: LLM, audit: Audit):
        self.db = db
        self.llm = llm
        self.audit = audit

    @property
    def skill(self):
        key = self.skill_name or self.name
        return self.llm.skill(key) if self.llm else None
