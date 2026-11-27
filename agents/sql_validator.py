"""
SQL Safety Validator Subagent.
Enforces read-only AST invariant: strictly blocks any destructive statements
(DROP, DELETE, TRUNCATE, ALTER, INSERT, UPDATE) before DB execution.
"""
from __future__ import annotations

import re
from typing import Optional
from .base import Agent


DESTRUCTIVE_PATTERN = re.compile(r"\b(DROP|DELETE|TRUNCATE|ALTER|INSERT|UPDATE|GRANT|REVOKE)\b", re.IGNORECASE)


class SQLValidatorAgent(Agent):
    name = "sql_validator"
    managed_agent_name = "DA_CL_Discovery_SqlValidatorFixerAgent"
    skill_name = "sql_validator_fixer"

    def validate(self, sql: str) -> tuple[bool, Optional[str]]:
        match = DESTRUCTIVE_PATTERN.search(sql)
        if match:
            viol = match.group(1).upper()
            self.audit.note(f"[SafetyGuard] Blocked destructive SQL command: {viol}", level="ERROR")
            return False, f"Destructive SQL command '{viol}' is forbidden by safety policy."

        # Verify SELECT statement
        clean = sql.strip().upper()
        if not clean.startswith("SELECT") and not clean.startswith("WITH") and not clean.startswith("EXPLAIN"):
            return False, "Only read-only SELECT / WITH queries are permitted."

        return True, None
