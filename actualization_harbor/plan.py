"""Plan with steps, dependencies, and scheduling."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class StepStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStatus(Enum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Step:
    """A single step in a plan."""
    name: str
    description: str = ""
    step_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    status: StepStatus = StepStatus.PENDING
    depends_on: List[str] = field(default_factory=list)  # step_ids
    estimated_duration: float = 0.0  # seconds, 0 = unknown
    actual_duration: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    def start(self) -> None:
        self.status = StepStatus.RUNNING
        self.started_at = time.time()

    def complete(self) -> None:
        self.status = StepStatus.COMPLETED
        self.completed_at = time.time()
        if self.started_at:
            self.actual_duration = self.completed_at - self.started_at

    def fail(self, error: str = "") -> None:
        self.status = StepStatus.FAILED
        self.error = error
        self.completed_at = time.time()
        if self.started_at:
            self.actual_duration = self.completed_at - self.started_at

    def skip(self) -> None:
        self.status = StepStatus.SKIPPED
        self.completed_at = time.time()

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def reset_for_retry(self) -> None:
        self.retry_count += 1
        self.status = StepStatus.PENDING
        self.error = None
        self.started_at = None
        self.completed_at = None


@dataclass
class Plan:
    """A plan composed of ordered/dependent steps."""
    name: str
    description: str = ""
    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal_id: Optional[str] = None
    status: PlanStatus = PlanStatus.DRAFT
    steps: List[Step] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    # -- building --

    def add_step(self, name: str, description: str = "",
                 depends_on: Optional[List[str]] = None,
                 estimated_duration: float = 0.0,
                 max_retries: int = 3) -> Step:
        step = Step(
            name=name, description=description,
            depends_on=depends_on or [],
            estimated_duration=estimated_duration,
            max_retries=max_retries,
        )
        self.steps.append(step)
        self.updated_at = time.time()
        return step

    def finalize(self) -> None:
        """Mark plan as ready — validates dependencies exist."""
        step_ids = {s.step_id for s in self.steps}
        for step in self.steps:
            step.depends_on = [d for d in step.depends_on if d in step_ids]
            step.status = StepStatus.READY if not step.depends_on else StepStatus.PENDING
        self.status = PlanStatus.READY
        self.updated_at = time.time()

    # -- execution helpers --

    def ready_steps(self) -> List[Step]:
        """Steps whose dependencies are all completed and are eligible to run."""
        completed_ids = {s.step_id for s in self.steps if s.status == StepStatus.COMPLETED}
        eligible = {StepStatus.PENDING, StepStatus.READY, StepStatus.FAILED}
        ready = []
        for step in self.steps:
            if step.status not in eligible:
                continue
            if step.status == StepStatus.FAILED and not step.can_retry:
                continue
            if all(d in completed_ids for d in step.depends_on):
                ready.append(step)
        return ready

    def all_completed(self) -> bool:
        return all(s.status == StepStatus.COMPLETED for s in self.steps)

    def any_failed(self) -> bool:
        return any(
            s.status == StepStatus.FAILED and not s.can_retry
            for s in self.steps
        )

    # -- progress --

    @property
    def progress(self) -> float:
        if not self.steps:
            return 1.0 if self.status == PlanStatus.COMPLETED else 0.0
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        return completed / len(self.steps)

    def start(self) -> None:
        self.status = PlanStatus.RUNNING
        self.updated_at = time.time()

    def complete(self) -> None:
        self.status = PlanStatus.COMPLETED
        self.completed_at = time.time()
        self.updated_at = time.time()

    def fail(self) -> None:
        self.status = PlanStatus.FAILED
        self.completed_at = time.time()
        self.updated_at = time.time()

    def cancel(self) -> None:
        self.status = PlanStatus.CANCELLED
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "goal_id": self.goal_id,
            "status": self.status.value,
            "progress": self.progress,
            "step_count": len(self.steps),
            "steps_completed": sum(1 for s in self.steps if s.status == StepStatus.COMPLETED),
            "steps_failed": sum(1 for s in self.steps if s.status == StepStatus.FAILED),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
