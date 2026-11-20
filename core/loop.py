"""
S1 - Agentic Loop Engine: generate ➔ validate ➔ execute ➔ (fix ➔ re-validate)*.
Coordinates iterative self-healing for SQL queries when syntax or schema errors occur.
"""
from __future__ import annotations

import time
from typing import Callable, Optional
from .audit import Audit
from .schemas import SQLItem


class AgenticLoop:
    def __init__(self, audit: Audit, max_retries: int = 3):
        self.audit = audit
        self.max_retries = max_retries

    def run_query_with_healing(self,
                               item: SQLItem,
                               execute_fn: Callable[[str], Any],
                               validate_fn: Callable[[str], tuple[bool, Optional[str]]],
                               fix_fn: Callable[[str, str], str]) -> SQLItem:
        """Runs S1 self-healing loop for a SQLItem."""
        attempt = 0
        current_sql = item.query_sql

        while attempt < self.max_retries:
            attempt += 1
            item.fix_attempts = attempt

            # 1. AST Validation
            is_valid, val_err = validate_fn(current_sql)
            if not is_valid:
                self.audit.note(f"[SelfHealing] SQL {item.sql_id} AST validation failed: {val_err}. Fixing...", level="WARNING")
                current_sql = fix_fn(current_sql, val_err or "AST Syntax Error")
                continue

            # 2. Database Execution
            t0 = time.perf_counter()
            try:
                raw_res = execute_fn(current_sql)
                duration_ms = (time.perf_counter() - t0) * 1000.0
                item.query_sql = current_sql
                item.status = "executed"
                item.result = raw_res
                item.duration_ms = round(duration_ms, 2)
                item.error = None

                # Extract scalar violation count if DQ check
                if item.category == "dq_check" and raw_res and len(raw_res) > 0:
                    try:
                        item.violation_count = int(raw_res[0][0])
                    except (ValueError, TypeError):
                        item.violation_count = len(raw_res)

                self.audit.sql_executed(item.sql_id, item.table_name, current_sql, item.duration_ms, item.violation_count)
                return item

            except Exception as db_err:
                duration_ms = (time.perf_counter() - t0) * 1000.0
                err_msg = str(db_err)
                self.audit.note(f"[SelfHealing] SQL {item.sql_id} execution attempt {attempt} failed: {err_msg}", level="WARNING")
                self.audit.sql_executed(item.sql_id, item.table_name, current_sql, duration_ms, 0, error=err_msg)
                current_sql = fix_fn(current_sql, err_msg)

        # Exhausted attempts
        item.status = "failed"
        item.error = f"Failed after {self.max_retries} self-healing attempts."
        return item
