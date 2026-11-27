"""
Governance Reviewer Subagent.
Triages table health into HEALTHY, NEEDS_ATTENTION, or DEGRADED based on DQ violation counts.
"""
from __future__ import annotations

from core.schemas import DQRule, TableHealth, TableHealthTriage, TableMeta
from .base import Agent


class ReviewerAgent(Agent):
    name = "governance_reviewer"
    managed_agent_name = "DA_CL_Discovery_GovernanceReviewerAgent"
    skill_name = "governance_reviewer"

    def review_table_health(self, table: TableMeta, rules: list[DQRule]) -> TableHealthTriage:
        table_rules = [r for r in rules if r.table_name == table.table_name]
        total = len(table_rules)
        if total == 0:
            return TableHealthTriage(
                table_name=table.table_name,
                health=TableHealth.HEALTHY.value,
                total_dq_checks=0,
                passed_dq_checks=0,
                failed_dq_checks=0,
                score=100.0,
                reasons=["No active DQ rules defined."]
            )

        passed = sum(1 for r in table_rules if r.passed)
        failed = total - passed
        score = round((passed / total) * 100.0, 1)

        critical_fails = [r for r in table_rules if not r.passed and r.severity == "CRITICAL"]
        reasons = []

        if critical_fails:
            health = TableHealth.DEGRADED.value
            for cf in critical_fails:
                reasons.append(f"Critical defect: {cf.assertion} ({cf.check_sql.violation_count} violations)")
        elif score < 70.0:
            health = TableHealth.DEGRADED.value
            reasons.append(f"High defect volume: {failed} of {total} checks failed ({score}% health).")
        elif score < 95.0 or failed > 0:
            health = TableHealth.NEEDS_ATTENTION.value
            for f in [r for r in table_rules if not r.passed][:3]:
                reasons.append(f"Quality warning: {f.assertion} ({f.check_sql.violation_count} violations)")
        else:
            health = TableHealth.HEALTHY.value
            reasons.append("All data quality checks passed without defects.")

        triage = TableHealthTriage(
            table_name=table.table_name,
            health=health,
            total_dq_checks=total,
            passed_dq_checks=passed,
            failed_dq_checks=failed,
            score=score,
            reasons=reasons
        )

        self.audit.agent_action(self.name, "table_reviewed", triage.to_dict())
        return triage
