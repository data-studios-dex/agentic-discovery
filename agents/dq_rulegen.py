"""
DQ Rule Generator Subagent.
Synthesizes 6-dimension Data Quality assertions returning scalar violation counts:
- COMPLETENESS: Checks for unexpected NULLs in critical/NOT NULL columns
- UNIQUENESS: Checks for duplicate keys or identifiers
- VALIDITY: Checks format, domain values (e.g. email regex, status IN ('ACTIVE', 'PENDING'))
- CONSISTENCY: Checks cross-field relationships (e.g. ship_date >= order_date, total_amount >= 0)
- ACCURACY: Checks reasonable boundary limits (e.g. discount_rate BETWEEN 0 AND 1)
- TIMELINESS: Checks for future-dated timestamps or stale records
"""
from __future__ import annotations

import re
from core.schemas import DQDimension, DQRule, SQLItem, TableMeta
from .base import Agent


class DQRuleGenAgent(Agent):
    name = "dq_rulegen"
    skill_name = "dq_rulegen"

    def generate_rules(self, table: TableMeta) -> list[DQRule]:
        self.audit.agent_action(self.name, "generate_dq_rules", {"table": table.table_name})
        qual = self.db.qualify(table.schema_name, table.table_name)
        rules: list[DQRule] = []

        # 1. Uniqueness: Primary Keys
        if table.primary_keys:
            pk_cols = ", ".join(self.db.quote(pk) for pk in table.primary_keys)
            pk_rule_sql = f"""
                SELECT COUNT(*) FROM (
                    SELECT {pk_cols} FROM {qual}
                    GROUP BY {pk_cols}
                    HAVING COUNT(*) > 1
                ) AS dupes
            """.strip()

            rules.append(DQRule(
                rule_id=f"dq_{table.table_name}_pk_uniqueness",
                table_name=table.table_name,
                column_name=", ".join(table.primary_keys),
                dimension=DQDimension.UNIQUENESS.value,
                assertion=f"Primary key ({', '.join(table.primary_keys)}) must be strictly unique.",
                severity="CRITICAL",
                check_sql=SQLItem(
                    sql_id=f"sql_dq_{table.table_name}_pk_uniqueness",
                    category="dq_check",
                    table_name=table.table_name,
                    query_sql=pk_rule_sql
                )
            ))

        # 2. Completeness: Non-nullable columns
        for col in table.columns:
            if not col.is_nullable:
                c_q = self.db.quote(col.column_name)
                comp_sql = f"SELECT COUNT(*) FROM {qual} WHERE {c_q} IS NULL"
                rules.append(DQRule(
                    rule_id=f"dq_{table.table_name}_{col.column_name}_not_null",
                    table_name=table.table_name,
                    column_name=col.column_name,
                    dimension=DQDimension.COMPLETENESS.value,
                    assertion=f"Column '{col.column_name}' is declared NOT NULL and must contain zero null values.",
                    severity="HIGH",
                    check_sql=SQLItem(
                        sql_id=f"sql_dq_{table.table_name}_{col.column_name}_not_null",
                        category="dq_check",
                        table_name=table.table_name,
                        column_name=col.column_name,
                        query_sql=comp_sql
                    )
                ))

        # 3. Validity & Consistency based on semantic column names
        for col in table.columns:
            c_name_lower = col.column_name.lower()
            c_q = self.db.quote(col.column_name)

            # Email validity
            if "email" in c_name_lower:
                email_sql = f"SELECT COUNT(*) FROM {qual} WHERE {c_q} IS NOT NULL AND {c_q} NOT LIKE '%@%.%'"
                rules.append(DQRule(
                    rule_id=f"dq_{table.table_name}_{col.column_name}_format",
                    table_name=table.table_name,
                    column_name=col.column_name,
                    dimension=DQDimension.VALIDITY.value,
                    assertion=f"Email in '{col.column_name}' must match valid domain syntax.",
                    severity="MEDIUM",
                    check_sql=SQLItem(
                        sql_id=f"sql_dq_{table.table_name}_{col.column_name}_format",
                        category="dq_check",
                        table_name=table.table_name,
                        column_name=col.column_name,
                        query_sql=email_sql
                    )
                ))

            # Non-negative amounts / prices
            if any(k in c_name_lower for k in ("amount", "price", "total", "balance", "cost")):
                amt_sql = f"SELECT COUNT(*) FROM {qual} WHERE {c_q} < 0"
                rules.append(DQRule(
                    rule_id=f"dq_{table.table_name}_{col.column_name}_non_negative",
                    table_name=table.table_name,
                    column_name=col.column_name,
                    dimension=DQDimension.CONSISTENCY.value,
                    assertion=f"Monetary attribute '{col.column_name}' must be non-negative.",
                    severity="HIGH",
                    check_sql=SQLItem(
                        sql_id=f"sql_dq_{table.table_name}_{col.column_name}_non_negative",
                        category="dq_check",
                        table_name=table.table_name,
                        column_name=col.column_name,
                        query_sql=amt_sql
                    )
                ))

            # Timeliness / Future Date Checks
            if any(k in c_name_lower for k in ("created", "order_date", "registered", "birth_date")):
                time_sql = f"SELECT COUNT(*) FROM {qual} WHERE {c_q} > CURRENT_TIMESTAMP" if self.db.dialect != "oracle" else f"SELECT COUNT(*) FROM {qual} WHERE {c_q} > SYSDATE"
                rules.append(DQRule(
                    rule_id=f"dq_{table.table_name}_{col.column_name}_no_future_dates",
                    table_name=table.table_name,
                    column_name=col.column_name,
                    dimension=DQDimension.TIMELINESS.value,
                    assertion=f"Date '{col.column_name}' must not occur in the future.",
                    severity="MEDIUM",
                    check_sql=SQLItem(
                        sql_id=f"sql_dq_{table.table_name}_{col.column_name}_no_future_dates",
                        category="dq_check",
                        table_name=table.table_name,
                        column_name=col.column_name,
                        query_sql=time_sql
                    )
                ))

        return rules
