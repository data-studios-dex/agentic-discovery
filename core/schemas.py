"""
S3 - Typed Context Passing & Data Governance Contracts.
Defines all dataclasses exchanged across subagents, quality gates G1-G6, and audit exporters.
"""
from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


def utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class TableHealth(str, Enum):
    HEALTHY = "HEALTHY"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    DEGRADED = "DEGRADED"


class DQDimension(str, Enum):
    COMPLETENESS = "COMPLETENESS"
    UNIQUENESS = "UNIQUENESS"
    VALIDITY = "VALIDITY"
    CONSISTENCY = "CONSISTENCY"
    ACCURACY = "ACCURACY"
    TIMELINESS = "TIMELINESS"


@dataclass
class ColumnMeta:
    column_name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False
    default_value: Optional[str] = None
    comment: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TableMeta:
    table_name: str
    schema_name: str = "main"
    columns: list[ColumnMeta] = field(default_factory=list)
    primary_keys: list[str] = field(default_factory=list)
    row_count: int = 0
    comment: Optional[str] = None

    def get_column(self, name: str) -> Optional[ColumnMeta]:
        name_lower = name.lower()
        for c in self.columns:
            if c.column_name.lower() == name_lower:
                return c
        return None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SchemaManifest:
    dialect: str
    schema_name: str = "main"
    database_url_masked: str = ""
    tables: list[TableMeta] = field(default_factory=list)

    @property
    def table_count(self) -> int:
        return len(self.tables)

    def get_table(self, name: str) -> Optional[TableMeta]:
        name_lower = name.lower()
        for t in self.tables:
            if t.table_name.lower() == name_lower:
                return t
        return None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SQLItem:
    sql_id: str
    category: str  # "profiling" | "dq_check"
    table_name: str
    column_name: Optional[str] = None
    query_sql: str = ""
    status: str = "pending"  # pending, validated, executed, failed, waived
    result: Any = None
    violation_count: int = 0
    duration_ms: float = 0.0
    error: Optional[str] = None
    fix_attempts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DQRule:
    rule_id: str
    table_name: str
    column_name: Optional[str]
    dimension: str  # COMPLETENESS, UNIQUENESS, etc.
    assertion: str
    check_sql: SQLItem
    threshold: int = 0  # violation tolerance (usually 0)
    severity: str = "HIGH"  # CRITICAL, HIGH, MEDIUM, LOW

    @property
    def passed(self) -> bool:
        return self.check_sql.status == "executed" and self.check_sql.violation_count <= self.threshold

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GateDecision:
    gate_id: str
    state: str  # "open" | "closed"
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TableHealthTriage:
    table_name: str
    health: str  # TableHealth
    total_dq_checks: int = 0
    passed_dq_checks: int = 0
    failed_dq_checks: int = 0
    score: float = 100.0  # 0.0 - 100.0%
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
