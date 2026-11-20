"""
Database Discovery Subagent.
Dynamically introspects database catalogs, tables, columns, constraints, and row counts
across SQLite, PostgreSQL, MySQL, Oracle, MSSQL, and Snowflake.
"""
from __future__ import annotations

import re
from core.db import mask_db_url
from core.schemas import ColumnMeta, SchemaManifest, TableMeta
from .base import Agent


class DiscoveryAgent(Agent):
    name = "db_discovery"
    skill_name = "db_discovery"

    def introspect(self, schema_name: str = "main", target_tables: list[str] = None) -> SchemaManifest:
        self.audit.agent_action(self.name, "start_introspection", {
            "dialect": self.db.dialect,
            "schema": schema_name,
            "filter_tables": target_tables
        })

        manifest = SchemaManifest(
            dialect=self.db.dialect,
            schema_name=schema_name,
            database_url_masked=mask_db_url(self.db.url)
        )

        table_names = self._get_table_names(schema_name)
        if target_tables:
            lower_targets = {t.lower() for t in target_tables}
            table_names = [t for t in table_names if t.lower() in lower_targets]

        for t_name in table_names:
            cols = self._get_columns(schema_name, t_name)
            pks = [c.column_name for c in cols if c.is_primary_key]
            row_cnt = self._get_row_count(schema_name, t_name)
            
            t_meta = TableMeta(
                table_name=t_name,
                schema_name=schema_name,
                columns=cols,
                primary_keys=pks,
                row_count=row_cnt
            )
            manifest.tables.append(t_meta)

        self.audit.agent_action(self.name, "introspection_complete", {
            "tables_found": manifest.table_count,
            "table_names": [t.table_name for t in manifest.tables]
        })
        return manifest

    def _get_table_names(self, schema: str) -> list[str]:
        dialect = self.db.dialect
        if dialect == "sqlite":
            rows = self.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            return [r[0] for r in rows]
        elif dialect in ("postgresql", "snowflake", "mysql"):
            sql = f"SELECT table_name FROM information_schema.tables WHERE table_schema='{schema}' AND table_type='BASE TABLE'"
            try:
                rows = self.db.execute(sql)
                return [r[0] for r in rows]
            except Exception:
                # Fallback to general query
                rows = self.db.execute("SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE'")
                return [r[0] for r in rows]
        else:
            # Generic fallback
            try:
                rows = self.db.execute("SELECT table_name FROM information_schema.tables")
                return [r[0] for r in rows]
            except Exception:
                return []

    def _get_columns(self, schema: str, table: str) -> list[ColumnMeta]:
        dialect = self.db.dialect
        cols = []

        if dialect == "sqlite":
            rows = self.db.execute(f"PRAGMA table_info({self.db.quote(table)})")
            for r in rows:
                # r: (cid, name, type, notnull, dflt_value, pk)
                cols.append(ColumnMeta(
                    column_name=r[1],
                    data_type=r[2] or "TEXT",
                    is_nullable=(r[3] == 0),
                    is_primary_key=(r[5] == 1),
                    default_value=str(r[4]) if r[4] is not None else None
                ))
        else:
            sql = f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name='{table}'
            """
            try:
                rows = self.db.execute(sql)
                for r in rows:
                    cols.append(ColumnMeta(
                        column_name=r[0],
                        data_type=r[1],
                        is_nullable=(str(r[2]).upper() == "YES")
                    ))
            except Exception:
                pass

        return cols

    def _get_row_count(self, schema: str, table: str) -> int:
        qual = self.db.qualify(schema, table)
        try:
            res = self.db.execute(f"SELECT COUNT(*) FROM {qual}")
            return int(res[0][0]) if res else 0
        except Exception:
            return 0
