"""
Secure Database Connection Profiles Manager for agentic-discovery.
Maintains zero-secret connection templates in connections.json, supports runtime password
prompting with getpass, environment variable fallback, and automated connection verification.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import datetime
import getpass
import json
import os
from pathlib import Path
import re
from typing import Any, Optional
from urllib.parse import quote

ROOT_DIR = Path(__file__).resolve().parent.parent
CONNECTIONS_FILE = Path(os.getenv("DISCOVERY_CONNECTIONS_FILE", str(ROOT_DIR / "connections.json")))


@dataclass
class ConnectionProfile:
    name: str
    dialect: str = "sqlite"
    url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    schema: str = "main"
    description: str = ""
    password_env_var: Optional[str] = None
    account: Optional[str] = None  # for Snowflake
    service_name: Optional[str] = None  # for Oracle

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @property
    def display_target(self) -> str:
        if self.dialect == "sqlite":
            return self.url or "sqlite:///sample/sample.db"
        if self.dialect == "snowflake":
            return f"snowflake://{self.username}@{self.account}/{self.database}/{self.schema}"
        return f"{self.dialect}://{self.username}@{self.host or 'localhost'}:{self.port or ''}/{self.database or self.schema}"


class ConnectionManager:
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or CONNECTIONS_FILE
        self._profiles: dict[str, ConnectionProfile] = {}
        self.load()

    def load(self) -> None:
        self._profiles.clear()
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        profile = ConnectionProfile(
                            name=v.get("name", k),
                            dialect=v.get("dialect", "sqlite"),
                            url=v.get("url"),
                            host=v.get("host"),
                            port=v.get("port"),
                            database=v.get("database"),
                            username=v.get("username"),
                            schema=v.get("schema", "main"),
                            description=v.get("description", ""),
                            password_env_var=v.get("password_env_var"),
                            account=v.get("account"),
                            service_name=v.get("service_name")
                        )
                        self._profiles[profile.name] = profile
            except Exception:
                pass

    def save(self) -> None:
        data = {name: p.to_dict() for name, p in self._profiles.items()}
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def list_connections(self) -> list[ConnectionProfile]:
        return list(self._profiles.values())

    def get_connection(self, name: str) -> Optional[ConnectionProfile]:
        return self._profiles.get(name)

    def resolve_url(self, profile: ConnectionProfile, runtime_password: Optional[str] = None, prompt_if_needed: bool = True) -> str:
        """
        Builds the active database URL in-memory.
        Never saves the resolved password to connections.json or tracked files.
        """
        if profile.dialect == "sqlite":
            return profile.url or "sqlite:///sample/sample.db"

        # Check password sources: 1) explicit, 2) env var, 3) interactive prompt
        password = runtime_password
        if not password and profile.password_env_var:
            password = os.getenv(profile.password_env_var)
        if not password:
            password = os.getenv("DB_PASSWORD")

        if not password and prompt_if_needed:
            try:
                password = getpass.getpass(f"Enter password for {profile.name} ({profile.username}@{profile.host or profile.account}): ")
            except (EOFError, KeyboardInterrupt):
                password = ""

        safe_pw = quote(password or "")
        user = quote(profile.username or "")

        if profile.dialect == "postgresql":
            return f"postgresql://{user}:{safe_pw}@{profile.host}:{profile.port or 5432}/{profile.database}"
        elif profile.dialect == "snowflake":
            return f"snowflake://{user}:{safe_pw}@{profile.account}/{profile.database}/{profile.schema}"
        elif profile.dialect == "oracle":
            return f"oracle+oracledb://{user}:{safe_pw}@{profile.host}:{profile.port or 1521}/?service_name={profile.service_name or 'ORCL'}"
        elif profile.dialect == "mysql":
            return f"mysql+pymysql://{user}:{safe_pw}@{profile.host}:{profile.port or 3306}/{profile.database}"
        else:
            return profile.url or f"{profile.dialect}://{user}:{safe_pw}@{profile.host}/{profile.database}"

    def add_connection(self,
                       name: str,
                       dialect: str,
                       host: Optional[str] = None,
                       port: Optional[int] = None,
                       database: Optional[str] = None,
                       username: Optional[str] = None,
                       schema: str = "main",
                       description: str = "",
                       url: Optional[str] = None) -> tuple[bool, str, ConnectionProfile]:
        """
        Saves a new zero-secret connection profile template to connections.json.
        """
        clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name.strip())
        if not clean_name:
            return False, "Connection profile name cannot be empty.", None

        profile = ConnectionProfile(
            name=clean_name,
            dialect=dialect.lower(),
            host=host,
            port=port,
            database=database,
            username=username,
            schema=schema or "main",
            description=description or f"Database connection template for {clean_name}",
            url=url,
            password_env_var=f"{clean_name.upper()}_PASSWORD" if dialect != "sqlite" else None
        )

        self._profiles[clean_name] = profile
        self.save()
        return True, f"Saved connection profile '{clean_name}' (password env var: {profile.password_env_var or 'None'}).", profile

    def test_connection(self, url: str) -> tuple[bool, str]:
        """Tests live database connectivity."""
        from .db import DB
        try:
            db = DB(url)
            ping_sql = "SELECT 1" if db.dialect != "oracle" else "SELECT 1 FROM DUAL"
            res = db.execute(ping_sql)
            if res and len(res) > 0:
                return True, f"Successfully connected to {db.dialect_label} (ping response: {res[0][0]})."
            return True, f"Connected to {db.dialect_label}."
        except Exception as e:
            return False, str(e)
