"""
Unit test suite for agentic-discovery framework.
Verifies connection management, discovery introspection, profiling, DQ rules, and Gates G1-G6.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from core.connections import ConnectionManager
from core.db import DB
from agents.sql_validator import SQLValidatorAgent
from core.orchestrator import DiscoveryOrchestrator


SAMPLE_DB_PATH = Path(__file__).resolve().parent.parent / "sample" / "sample.db"


class TestDiscoveryPipeline(unittest.TestCase):
    def test_connection_manager(self):
        mgr = ConnectionManager()
        conns = mgr.list_connections()
        self.assertGreaterEqual(len(conns), 1)

        sqlite_prof = mgr.get_connection("sqlite_sample")
        self.assertIsNotNone(sqlite_prof)
        self.assertEqual(sqlite_prof.dialect, "sqlite")

        # Test connection ping
        ok, msg = mgr.test_connection(f"sqlite:///{SAMPLE_DB_PATH}")
        self.assertTrue(ok)

    def test_sql_safety_validator(self):
        db = DB(f"sqlite:///{SAMPLE_DB_PATH}")
        from core.audit import Audit
        audit = Audit("test_audit", Path(tempfile.mkdtemp()))
        validator = SQLValidatorAgent(db, None, audit)

        # Safe read query
        is_safe, _ = validator.validate("SELECT * FROM customers")
        self.assertTrue(is_safe)

        # Block destructive query
        is_safe, reason = validator.validate("DROP TABLE customers")
        self.assertFalse(is_safe)
        self.assertIn("DROP", reason)

        is_safe, reason = validator.validate("DELETE FROM orders WHERE order_id = 1")
        self.assertFalse(is_safe)
        self.assertIn("DELETE", reason)

    def test_end_to_end_discovery_pipeline(self):
        tmp_dir = Path(tempfile.mkdtemp())
        db_url = f"sqlite:///{SAMPLE_DB_PATH}"

        orchestrator = DiscoveryOrchestrator(
            db_url=db_url,
            base_dir=tmp_dir,
            llm_mode="offline"
        )

        reports = orchestrator.run_pipeline(schema_name="main", mode="both")

        self.assertIn("html", reports)
        self.assertIn("markdown", reports)
        self.assertIn("audit", reports)

        self.assertTrue(Path(reports["html"]).exists())
        self.assertTrue(Path(reports["markdown"]).exists())
        self.assertTrue(Path(reports["audit"]).exists())

        # Verify audit summary
        summary = orchestrator.audit.summary()
        self.assertGreater(summary["total_events"], 5)
        self.assertEqual(summary["gate_decisions"], 6)


if __name__ == "__main__":
    unittest.main()
