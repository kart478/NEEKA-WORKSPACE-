import logging

from neeka.brain.exceptions import AutomationLoopError
from neeka.brain.event import Event
from neeka.persistence.repositories import AutomationExecutionRepository
from .rules import AutomationRule, dependency_completion_rule

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Routes events through deterministic rules with durable idempotency records."""

    def __init__(self, engine, executions: AutomationExecutionRepository, max_depth: int = 10) -> None:
        self.engine = engine
        self.executions = executions
        self.max_depth = max_depth
        self.rules: list[AutomationRule] = [dependency_completion_rule()]

    def add_rule(self, rule: AutomationRule) -> None:
        self.rules.append(rule)

    def process_event(self, event: Event, retry_failed: bool = False) -> None:
        depth = int(event.metadata.get("_automation_depth", 0))
        if depth > self.max_depth:
            raise AutomationLoopError(f"Automation depth exceeded {self.max_depth}")
        for rule in self.rules:
            if rule.trigger != event.event_type or not rule.condition(self.engine, event):
                continue
            execution_id = self.executions.start(event.id, rule.rule_id)
            if execution_id is None:
                existing = next(
                    (record for record in self.executions.list()
                     if record["event_id"] == event.id and record["rule_id"] == rule.rule_id),
                    None,
                )
                if retry_failed and existing and existing["status"] == "FAILED":
                    execution_id = self.executions.retry(event.id, rule.rule_id)
                else:
                    continue
            try:
                rule.action.execute(self.engine, event)
            except Exception as error:
                self.executions.finish(execution_id, "FAILED", str(error))
                logger.exception("Automation rule failed: %s", rule.rule_id)
                raise
            self.executions.finish(execution_id, "SUCCESS")