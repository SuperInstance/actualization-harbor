"""Goal definition with milestones, progress tracking, and decomposition."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class GoalStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class Milestone:
    """A measurable checkpoint within a goal."""
    name: str
    description: str = ""
    target_value: float = 1.0
    current_value: float = 0.0
    completed: bool = False
    completed_at: Optional[float] = None

    @property
    def progress(self) -> float:
        """Return progress as 0.0–1.0."""
        if self.target_value == 0:
            return 1.0 if self.completed else 0.0
        return min(1.0, max(0.0, self.current_value / self.target_value))

    def update(self, value: float) -> None:
        self.current_value = value
        if self.current_value >= self.target_value:
            self.completed = True
            self.completed_at = time.time()

    def complete(self) -> None:
        self.completed = True
        self.current_value = self.target_value
        self.completed_at = time.time()


@dataclass
class Goal:
    """A goal with milestones, progress tracking, and optional decomposition into sub-goals."""
    name: str
    description: str = ""
    goal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: GoalStatus = GoalStatus.PENDING
    priority: int = 0  # higher = more important
    parent_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    milestones: List[Milestone] = field(default_factory=list)
    sub_goals: List[str] = field(default_factory=list)  # goal_ids of children
    metadata: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    deadline: Optional[float] = None

    # -- mutators --

    def activate(self) -> None:
        self.status = GoalStatus.ACTIVE
        self.updated_at = time.time()

    def pause(self) -> None:
        if self.status == GoalStatus.ACTIVE:
            self.status = GoalStatus.PAUSED
            self.updated_at = time.time()

    def resume(self) -> None:
        if self.status == GoalStatus.PAUSED:
            self.status = GoalStatus.ACTIVE
            self.updated_at = time.time()

    def complete(self) -> None:
        self.status = GoalStatus.COMPLETED
        self.completed_at = time.time()
        self.updated_at = time.time()
        for m in self.milestones:
            if not m.completed:
                m.complete()

    def fail(self) -> None:
        self.status = GoalStatus.FAILED
        self.updated_at = time.time()

    def cancel(self) -> None:
        self.status = GoalStatus.CANCELLED
        self.updated_at = time.time()

    # -- milestones --

    def add_milestone(self, name: str, description: str = "",
                      target_value: float = 1.0) -> Milestone:
        m = Milestone(name=name, description=description, target_value=target_value)
        self.milestones.append(m)
        self.updated_at = time.time()
        return m

    def update_milestone(self, index: int, value: float) -> None:
        if 0 <= index < len(self.milestones):
            self.milestones[index].update(value)
            self.updated_at = time.time()

    # -- progress --

    @property
    def progress(self) -> float:
        """Overall progress 0.0–1.0 based on milestones."""
        if not self.milestones:
            return 1.0 if self.status == GoalStatus.COMPLETED else 0.0
        return sum(m.progress for m in self.milestones) / len(self.milestones)

    @property
    def is_overdue(self) -> bool:
        if self.deadline is None:
            return False
        return time.time() > self.deadline and self.status not in (
            GoalStatus.COMPLETED, GoalStatus.CANCELLED
        )

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "parent_id": self.parent_id,
            "tags": self.tags,
            "progress": self.progress,
            "milestone_count": len(self.milestones),
            "milestones_completed": sum(1 for m in self.milestones if m.completed),
            "sub_goal_count": len(self.sub_goals),
            "is_overdue": self.is_overdue,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "deadline": self.deadline,
        }
