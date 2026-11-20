"""
Query Fixer Subagent (S1 Agentic Self-Healing).
Repairs failing SQL queries automatically by applying dialect quoting,
correcting reserved words, or repairing syntax.
"""
from __future__ import annotations

import re
from .base import Agent


class QueryFixerAgent(Agent):
    name = "query_fixer"
    skill_name = "sql_validator_fixer"

    def repair_query(self, sql: str, error_message: str) -> str:
        fixed = sql

        # Fix reserved keyword identifier quoting (e.g. ORDER -> "ORDER" / `ORDER`)
        keywords = ["ORDER", "GROUP", "BY", "SELECT", "WHERE", "FROM", "TABLE", "USER", "KEY", "INDEX", "STATUS"]
        for kw in keywords:
            pattern = rf"\b({kw})\b"
            quoted_kw = self.db.quote(kw)
            if re.search(pattern, fixed, re.IGNORECASE) and quoted_kw not in fixed:
                # Replace only column references like t.ORDER or col ORDER
                fixed = re.sub(rf"(?<=\.)\b{kw}\b", quoted_kw, fixed, flags=re.IGNORECASE)

        # Fix SQLite datetime functions
        if self.db.dialect == "sqlite" and "CURRENT_TIMESTAMP()" in fixed:
            fixed = fixed.replace("CURRENT_TIMESTAMP()", "CURRENT_TIMESTAMP")

        return fixed
