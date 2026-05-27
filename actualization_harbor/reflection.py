"""ReflectionEngine — analyze outcomes and extract lessons."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .execution import ExecutionResult
from .goal import Goal, GoalStatus
from .plan import Plan, StepStatus


@dataclass
class Lesson:
    """A lesson extracted from reflection."""
    title: str
    description: str
    category: str  # e.g. "timing", "dependency", "retry", "scope"
    severity: str = "info"  # info, warning, critical
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Reflection:
    """Result of reflecting on a completed or failed execution."""
    plan_id: str
    goal_id: Optional[str]
    success: bool
    lessons: List[Lesson]
    summary: str
    scores: Dict[str, float]  # e.g. {"efficiency": 0.8, "reliability": 0.9}
    created_at: float = field(default_factory=time.time)


class ReflectionEngine:
    """Analyzes execution outcomes and extracts lessons.

    Usage:
        engine = ReflectionEngine()
        reflection = engine.reflect(plan, result, goal)
        for lesson in reflection.lessons:
            print(f"[{lesson.severity}] {lesson.title}")
    """

    def __init__(self):
        self.reflections: List[Reflection] = []

    def reflect(
        self,
        plan: Plan,
        result: ExecutionResult,
        goal: Optional[Goal] = None,
    ) -> Reflection:
        """Analyze a plan execution and produce a reflection."""
        lessons: List[Lesson] = []
        scores: Dict[str, float] = {}

        # -- analyze retries --
        total_retries = sum(s.retry_count for s in plan.steps)
        steps_with_retries = [s for s in plan.steps if s.retry_count > 0]
        if steps_with_retries:
            lesson = Lesson(
                title="Steps required retries",
                description=f"{len(steps_with_retries)} step(s) needed retries "
                            f"({total_retries} total). Steps: "
                            + ", ".join(s.name for s in steps_with_retries),
                category="retry",
                severity="warning" if total_retries <= 5 else "critical",
            )
            lessons.append(lesson)

        # -- analyze failed steps --
        failed_steps = [s for s in plan.steps if s.status == StepStatus.FAILED]
        if failed_steps:
            lesson = Lesson(
                title="Steps failed",
                description=f"{len(failed_steps)} step(s) failed: "
                            + "; ".join(f"{s.name}: {s.error or 'unknown'}" for s in failed_steps),
                category="failure",
                severity="critical",
            )
            lessons.append(lesson)

        # -- analyze timing --
        steps_with_estimate = [s for s in plan.steps if s.estimated_duration > 0]
        if steps_with_estimate:
            over_budget = [
                s for s in steps_with_estimate
                if s.actual_duration > s.estimated_duration * 1.5
            ]
            if over_budget:
                lesson = Lesson(
                    title="Steps over time budget",
                    description=f"{len(over_budget)} step(s) exceeded 1.5x estimated duration: "
                                + ", ".join(s.name for s in over_budget),
                    category="timing",
                    severity="warning",
                )
                lessons.append(lesson)

        # -- analyze skipped steps --
        skipped = [s for s in plan.steps if s.status == StepStatus.SKIPPED]
        if skipped:
            lesson = Lesson(
                title="Steps were skipped",
                description=f"{len(skipped)} step(s) skipped due to upstream failures: "
                            + ", ".join(s.name for s in skipped),
                category="dependency",
                severity="warning",
            )
            lessons.append(lesson)

        # -- compute scores --
        total_steps = len(plan.steps)
        if total_steps > 0:
            scores["completion_rate"] = result.steps_completed / total_steps
            scores["failure_rate"] = result.steps_failed / total_steps

        if steps_with_estimate:
            avg_ratio = (
                sum(s.actual_duration / s.estimated_duration for s in steps_with_estimate)
                / len(steps_with_estimate)
            )
            scores["timing_accuracy"] = min(1.0, 1.0 / max(avg_ratio, 0.01))

        if total_retries == 0:
            scores["reliability"] = 1.0
        elif total_steps > 0:
            scores["reliability"] = max(0.0, 1.0 - (total_retries / total_steps))

        if result.total_duration > 0 and total_steps > 0:
            scores["throughput"] = result.steps_completed / result.total_duration

        # -- generate summary --
        if result.success:
            summary = (
                f"Plan '{plan.name}' completed successfully. "
                f"{result.steps_completed}/{total_steps} steps done "
                f"in {result.total_duration:.2f}s "
                f"with {result.retries_used} retries."
            )
        else:
            summary = (
                f"Plan '{plan.name}' failed. "
                f"{result.steps_completed}/{total_steps} steps completed, "
                f"{result.steps_failed} failed, "
                f"{result.steps_skipped} skipped. "
                f"{len(lessons)} lessons extracted."
            )

        # -- goal alignment --
        if goal:
            if result.success and goal.progress >= 0.9:
                lesson = Lesson(
                    title="Goal alignment: strong",
                    description=f"Plan completion aligns well with goal '{goal.name}' "
                                f"(progress: {goal.progress:.0%})",
                    category="alignment",
                    severity="info",
                )
                lessons.append(lesson)
            elif result.success and goal.progress < 0.5:
                lesson = Lesson(
                    title="Goal alignment: weak",
                    description=f"Plan succeeded but goal '{goal.name}' is only "
                                f"{goal.progress:.0%} complete — plan scope may be too narrow",
                    category="alignment",
                    severity="warning",
                )
                lessons.append(lesson)

        reflection = Reflection(
            plan_id=plan.plan_id,
            goal_id=goal.goal_id if goal else None,
            success=result.success,
            lessons=lessons,
            summary=summary,
            scores=scores,
        )
        self.reflections.append(reflection)
        return reflection

    def get_lessons_by_category(self, category: str) -> List[Lesson]:
        return [
            lesson
            for r in self.reflections
            for lesson in r.lessons
            if lesson.category == category
        ]

    def get_lessons_by_severity(self, severity: str) -> List[Lesson]:
        return [
            lesson
            for r in self.reflections
            for lesson in r.lessons
            if lesson.severity == severity
        ]
