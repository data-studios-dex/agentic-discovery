"""
S5 - Pre-Tool Safety Guardrail for Database Discovery & Auditing.
Blocks destructive statements (DROP, DELETE, TRUNCATE, ALTER, INSERT, UPDATE, GRANT).
"""
from __future__ import annotations

import re
import sys

DESTRUCTIVE_PATTERN = re.compile(r"\b(DROP|DELETE|TRUNCATE|ALTER|INSERT|UPDATE|GRANT|REVOKE)\b", re.IGNORECASE)


def audit_sql_safety(sql: str) -> tuple[bool, str]:
    match = DESTRUCTIVE_PATTERN.search(sql)
    if match:
        return False, f"Destructive SQL command '{match.group(1).upper()}' blocked by safety guardrail"
    return True, "Safe read-only statement"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
        ok, reason = audit_sql_safety(query)
        if not ok:
            print(f"[SECURITY BLOCKED] {reason}", file=sys.stderr)
            sys.exit(1)
        print("[SECURITY ALLOWED] Safe read-only expression")
        sys.exit(0)
