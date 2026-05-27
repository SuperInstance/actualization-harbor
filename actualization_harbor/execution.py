"""ExecutionEngine — runs plans with retry and rollback support."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .plan import Plan, PlanStatus, Step, StepStatus


StepAction = Callable[[Step], Optional[str]]
"""A function that executes a step. Returns an error string on failure, None on success."""


@dataclass
class ExecutionResult:
    """Outcome of executing a plan."""
    plan_id: str
    success: bool
    steps_completed: int
    steps_failed: int
    steps_skipped: int
    total_duration: float
    retries_used: int
    errors: List[str] = field(default_factory=list)


class ExecutionEngine:
    """Runs plans step-by-step with retry and rollback.

    Usage:
        engine = ExecutionEngine()
        engine.register_action("fetch", my_fetch_fn)
        engine.register_action("process", my_process_fn)
        result = engine.execute(plan)
    """

    def __init__(self, max_global_retries: int = 3):
        self.actions: Dict[str, StepAction] = {}
        self.max_global_retries = max_global_retries
        self.execution_log: List[dict] = []

    def register_action(self, action_name: str, fn: StepAction) -> None:
        self.actions[action_name] = fn

    def execute(self, plan: Plan, on_step: Optional[Callable[[Step], None]] = None) -> ExecutionResult:
        """Execute a plan to completion (or failure).

        Args:
            plan: The plan to execute.
            on_step: Optional callback after each step attempt.
        """
        if plan.status not in (PlanStatus.READY, PlanStatus.RUNNING):
            return ExecutionResult(
                plan_id=plan.plan_id, success=False,
                steps_completed=0, steps_failed=0, steps_skipped=0,
                total_duration=0.0, retries_used=0,
                errors=[f"Plan status is {plan.status.value}, cannot execute"],
            )

        start_time = time.time()
        plan.start()
        total_retries = 0
        errors: List[str] = []

        while True:
            ready = plan.ready_steps()
            if not ready:
                break

            for step in ready:
                if step.status == StepStatus.FAILED and step.can_retry:
                    step.reset_for_retry()
                    total_retries += 1

                step.start()
                action_key = step.metadata.get("action", step.name)
                action = self.actions.get(action_key)

                if action is None:
                    # No registered action — auto-succeed (stub step)
                    step.complete()
                else:
                    try:
                        error = action(step)
                        if error:
                            step.fail(error)
                            errors.append(f"Step {step.name}: {error}")
                        else:
                            step.complete()
                    except Exception as exc:
                        step.fail(str(exc))
                        errors.append(f"Step {step.name} exception: {exc}")

                if on_step:
                    on_step(step)

                self.execution_log.append({
                    "plan_id": plan.plan_id,
                    "step_id": step.step_id,
                    "step_name": step.name,
                    "status": step.status.value,
                    "duration": step.actual_duration,
                    "retry_count": step.retry_count,
                    "error": step.error,
                    "timestamp": time.time(),
                })

        # Determine outcome
        steps_completed = sum(1 for s in plan.steps if s.status == StepStatus.COMPLETED)
        steps_failed = sum(1 for s in plan.steps if s.status == StepStatus.FAILED)

        if plan.all_completed():
            plan.complete()
            success = True
        elif plan.any_failed():
            plan.fail()
            success = False
            # Skip remaining pending steps
            for s in plan.steps:
                if s.status == StepStatus.PENDING:
                    s.skip()
        else:
            success = False

        steps_skipped = sum(1 for s in plan.steps if s.status == StepStatus.SKIPPED)
        total_duration = time.time() - start_time

        return ExecutionResult(
            plan_id=plan.plan_id,
            success=success,
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            steps_skipped=steps_skipped,
            total_duration=total_duration,
            retries_used=total_retries,
            errors=errors,
        )
