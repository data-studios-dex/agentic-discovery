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

    def test_managed_agents_naming_convention(self):
        from core.managed_agents import ManagedAgentRegistry, check_managed_agents, MANAGED_AGENTS_SPEC

        ok, drifts = check_managed_agents()
        self.assertTrue(ok, f"Managed agents drift detected: {drifts}")

        registry = ManagedAgentRegistry()
        for spec in MANAGED_AGENTS_SPEC:
            agent_name = spec["agent_name"]
            # Enforce DA_CL_{UseCase}_{AgentName}
            self.assertTrue(agent_name.startswith("DA_CL_Discovery_"), f"Invalid prefix: {agent_name}")
            self.assertTrue(agent_name.endswith("Agent"), f"Invalid suffix: {agent_name}")

            entry = registry.get_agent(agent_name)
            self.assertIsNotNone(entry, f"Missing managed agent entry for {agent_name}")
            self.assertEqual(entry.get("agent_name"), agent_name)

            # Test skill alias resolution
            skill_entry = registry.get_agent(spec["skill"])
            self.assertIsNotNone(skill_entry, f"Alias lookup failed for skill {spec['skill']}")
            self.assertEqual(skill_entry.get("agent_name"), agent_name)

    def test_nlp_qa_engine(self):
        from core.qa_engine import DiscoveryQAEngine
        tmp_dir = Path(tempfile.mkdtemp())
        db_url = f"sqlite:///{SAMPLE_DB_PATH}"

        orchestrator = DiscoveryOrchestrator(
            db_url=db_url,
            base_dir=tmp_dir,
            llm_mode="offline"
        )
        orchestrator.run_pipeline(schema_name="main", mode="both")

        qa = DiscoveryQAEngine(base_dir=tmp_dir, run_id=orchestrator.run_id)

        # 1. Test violations query
        ans_viol = qa.answer_question("Show all data quality violations")
        self.assertIn("Violations Detected", ans_viol)

        # 2. Test remediation query
        ans_fix = qa.answer_question("How to fix defects in table customers?")
        self.assertIn("Recommended SQL Remediation", ans_fix)

        # 3. Test schema structure query
        ans_schema = qa.answer_question("Show structure and columns of table orders")
        self.assertIn("Table Schema Architecture", ans_schema)

        # 4. Test table health query
        ans_health = qa.answer_question("Show me health status of all tables")
        self.assertIn("Overall Table Health Triage", ans_health)


if __name__ == "__main__":
    unittest.main()
