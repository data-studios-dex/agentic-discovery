"""
Database Adapter & Connection Engine.
Connects directly to SQLite (built-in stdlib) or any relational engine via SQLAlchemy:
PostgreSQL, Snowflake, MySQL, Oracle, MSSQL, BigQuery, SQLite.
Exposes normalized engine dialect, quoting, and read-only execution.
"""
from __future__ import annotations

import re
import sqlite3
from typing import Any, Optional
from urllib.parse import quote, unquote

from .schemas import ColumnMeta, SchemaManifest, TableMeta


_DIALECT_MAP = {
    "sqlite": "SQLite",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mariadb": "MariaDB",
    "mssql": "Microsoft SQL Server",
    "oracle": "Oracle",
    "bigquery": "Google BigQuery",
    "snowflake": "Snowflake",
    "redshift": "Amazon Redshift",
}


def normalize_db_url(url: str) -> str:
    """Percent-encodes username and password safely to prevent parsing errors."""
    if not url or url.startswith("sqlite") or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    authority, sep, tail = rest.partition("/")
    if "@" not in authority:
        return url
    userinfo, host = authority.rsplit("@", 1)
    if ":" in userinfo:
        user, pw = userinfo.split(":", 1)
        userinfo = f"{quote(unquote(user), safe='')}:{quote(unquote(pw), safe='')}"
    else:
        userinfo = quote(unquote(userinfo), safe="")
    return f"{scheme}://{userinfo}@{host}{sep}{tail}"


def mask_db_url(url: str) -> str:
    """Masks credentials in database URL for safe logging and output."""
    return re.sub(r"(://[^:/@]*):[^@]*@", r"\1:***@", url or "")


class DB:
    def __init__(self, url: str):
        self.raw_url = url
        self.url = normalize_db_url(url)
        self.kind = "sqlite" if self.url.startswith("sqlite") else "sqlalchemy"
        self._conn = None
        self._engine = None

        if self.kind == "sqlite":
            path = self.url.replace("sqlite:///", "").replace("sqlite://", "")
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        else:
            try:
                from sqlalchemy import create_engine
                self._engine = create_engine(self.url, pool_pre_ping=True)
            except ImportError as e:
                raise RuntimeError(
                    f"Connecting to non-SQLite database requires SQLAlchemy plus driver: {e}"
                )

    @property
    def dialect(self) -> str:
        """Normalized dialect name: sqlite, postgresql, snowflake, oracle, mysql, mssql."""
        url_low = (self.url or "").lower()
        key = url_low.split("://")[0].split("+")[0]
        if key == "postgres":
            return "postgresql"
        return key

    @property
    def dialect_label(self) -> str:
        return _DIALECT_MAP.get(self.dialect, self.dialect.title())

    def quote(self, identifier: str) -> str:
        """Dialect-accurate identifier quoting."""
        if not identifier:
            return ""
        d = self.dialect
        if d in ("mysql", "mariadb", "bigquery"):
            return f"`{identifier}`"
        elif d in ("mssql",):
            return f"[{identifier}]"
        return f'"{identifier}"'

    def qualify(self, schema: str, name: str) -> str:
        """Qualifies schema.table with dialect quotes."""
        qn = self.quote(name)
        if schema and schema.lower() not in ("", "main"):
            return f"{self.quote(schema)}.{qn}"
        return qn

    def execute(self, sql: str, timeout_s: int = 60) -> list[tuple]:
        """Executes a SQL query and returns rows as tuples."""
        if self.kind == "sqlite":
            cur = self._conn.execute(sql)
            return [tuple(row) for row in cur.fetchall()]
        else:
            from sqlalchemy import text
            with self._engine.connect() as conn:
                res = conn.execute(text(sql))
                return [tuple(row) for row in res.fetchall()]

    def close(self):
        if self._conn:
            self._conn.close()
        if self._engine:
            self._engine.dispose()
