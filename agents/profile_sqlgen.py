"""
SQL Profiler Subagent.
Formulates read-only statistical data profiling queries:
volume, nullability, cardinality, and boundary values.
"""
from __future__ import annotations

from core.schemas import SQLItem, TableMeta
from .base import Agent


class SQLProfilerAgent(Agent):
    name = "sql_profiler"
    skill_name = "sql_profiler"

    def formulate_profiling(self, table: TableMeta) -> list[SQLItem]:
        self.audit.agent_action(self.name, "formulate_profile_sql", {"table": table.table_name})
        qual = self.db.qualify(table.schema_name, table.table_name)
        items = []

        # 1. Total Volume
        items.append(SQLItem(
            sql_id=f"prof_{table.table_name}_volume",
            category="profiling",
            table_name=table.table_name,
            query_sql=f"SELECT COUNT(*) AS total_rows FROM {qual}"
        ))

        # 2. Per-column null count & distinct count
        for col in table.columns:
            c_quoted = self.db.quote(col.column_name)
            sql = f"""
                SELECT 
                    COUNT(*) - COUNT({c_quoted}) AS null_count,
                    COUNT(DISTINCT {c_quoted}) AS distinct_count
                FROM {qual}
            """.strip()

            items.append(SQLItem(
                sql_id=f"prof_{table.table_name}_{col.column_name}_stats",
                category="profiling",
                table_name=table.table_name,
                column_name=col.column_name,
                query_sql=sql
            ))

        return items
