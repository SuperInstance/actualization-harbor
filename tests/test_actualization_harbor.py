"""Comprehensive tests for actualization-harbor."""

import time
import pytest

from actualization_harbor import (
    ActualizationHarbor, Goal, GoalStatus, Milestone,
    Plan, PlanStatus, Step, StepStatus,
    ExecutionEngine, ExecutionResult,
    Reflection, ReflectionEngine, Lesson,
    AgentProfile, FlowState, Adaptation,
)


# ============================================================
# Legacy harbor tests (preserved from original)
# ============================================================

class TestLegacyHarbor:
    def test_register_and_enter(self):
        h = ActualizationHarbor()
        h.register("agent-1", model_type="llm-7b", context_window=4096)
        state = h.enter("agent-1")
        assert state == FlowState.ENTERING
        assert h.profiles["agent-1"].visits == 1

    def test_full_cycle(self):
        h = ActualizationHarbor()
        h.register("a")
        h.enter("a")
        h.train("a")
        h.integrate("a")
        h.depart("a")
        assert h.state("a") == FlowState.DEPARTING

    def test_assess_adaptations(self):
        h = ActualizationHarbor()
        h.register("smart", model_type="llm-70b", context_window=8192,
                    capabilities=["code", "math", "reasoning", "writing"])
        h.enter("smart")
        adaptations = h.assess("smart")
        assert len(adaptations) >= 2
        params = {p: v for a in adaptations for p, v in a.parameters.items()}
        assert "batch_size" in params

    def test_cannot_train_without_enter(self):
        h = ActualizationHarbor()
        h.register("a")
        assert not h.train("a")

    def test_docked_agents(self):
        h = ActualizationHarbor()
        h.register("a")
        h.register("b")
        h.enter("a")
        h.enter("b")
        h.train("a")
        assert len(h.docked_agents()) == 2

    def test_auto_register_on_enter(self):
        h = ActualizationHarbor()
        h.enter("unknown-agent")
        assert "unknown-agent" in h.profiles
        assert h.profiles["unknown-agent"].visits == 1

    def test_stats(self):
        h = ActualizationHarbor()
        h.register("a")
        h.register("b")
        h.enter("a")
        stats = h.stats()
        assert stats["registered"] == 2
        assert stats["total_visits"] == 1


# ============================================================
# Goal tests
# ============================================================

class TestGoal:
    def test_create_goal(self):
        g = Goal(name="Test goal")
        assert g.status == GoalStatus.PENDING
        assert g.progress == 0.0

    def test_activate(self):
        g = Goal(name="x")
        g.activate()
        assert g.status == GoalStatus.ACTIVE

    def test_lifecycle(self):
        g = Goal(name="x")
        g.activate()
        g.pause()
        assert g.status == GoalStatus.PAUSED
        g.resume()
        assert g.status == GoalStatus.ACTIVE
        g.complete()
        assert g.status == GoalStatus.COMPLETED
        assert g.completed_at is not None

    def test_fail(self):
        g = Goal(name="x")
        g.activate()
        g.fail()
        assert g.status == GoalStatus.FAILED

    def test_cancel(self):
        g = Goal(name="x")
        g.cancel()
        assert g.status == GoalStatus.CANCELLED

    def test_milestones(self):
        g = Goal(name="Build feature")
        g.add_milestone("Design", target_value=1.0)
        g.add_milestone("Implement", target_value=100.0)
        assert len(g.milestones) == 2
        assert g.progress == 0.0

    def test_milestone_update(self):
        g = Goal(name="x")
        g.add_milestone("Step 1", target_value=1.0)
        g.add_milestone("Step 2", target_value=1.0)
        g.update_milestone(0, 1.0)
        assert g.milestones[0].completed
        assert g.progress == pytest.approx(0.5)

    def test_complete_auto_completes_milestones(self):
        g = Goal(name="x")
        g.add_milestone("A")
        g.add_milestone("B")
        g.complete()
        assert all(m.completed for m in g.milestones)
        assert g.progress == 1.0

    def test_progress_with_no_milestones(self):
        g = Goal(name="x")
        assert g.progress == 0.0
        g.complete()
        assert g.progress == 1.0

    def test_is_overdue(self):
        g = Goal(name="x", deadline=time.time() - 100)
        assert g.is_overdue
        g.complete()
        assert not g.is_overdue

    def test_not_overdue_no_deadline(self):
        g = Goal(name="x")
        assert not g.is_overdue

    def test_to_dict(self):
        g = Goal(name="Test", tags=["a", "b"])
        d = g.to_dict()
        assert d["name"] == "Test"
        assert d["status"] == "pending"
        assert d["tags"] == ["a", "b"]

    def test_unique_ids(self):
        g1 = Goal(name="a")
        g2 = Goal(name="b")
        assert g1.goal_id != g2.goal_id


class TestMilestone:
    def test_progress(self):
        m = Milestone(name="x", target_value=10.0, current_value=5.0)
        assert m.progress == pytest.approx(0.5)

    def test_complete(self):
        m = Milestone(name="x", target_value=1.0)
        m.complete()
        assert m.completed
        assert m.current_value == 1.0

    def test_auto_complete_on_update(self):
        m = Milestone(name="x", target_value=5.0)
        m.update(5.0)
        assert m.completed
        assert m.completed_at is not None

    def test_zero_target(self):
        m = Milestone(name="x", target_value=0)
        assert m.progress == 0.0
        m.complete()
        assert m.progress == 1.0

    def test_clamp_progress(self):
        m = Milestone(name="x", target_value=5.0, current_value=10.0)
        assert m.progress == 1.0


# ============================================================
# Plan tests
# ============================================================

class TestPlan:
    def test_create_plan(self):
        p = Plan(name="Test plan")
        assert p.status == PlanStatus.DRAFT

    def test_add_steps(self):
        p = Plan(name="x")
        s1 = p.add_step("Step 1")
        s2 = p.add_step("Step 2", depends_on=[s1.step_id])
        assert len(p.steps) == 2
        assert s2.depends_on == [s1.step_id]

    def test_finalize(self):
        p = Plan(name="x")
        s1 = p.add_step("A")
        s2 = p.add_step("B", depends_on=[s1.step_id])
        p.finalize()
        assert p.status == PlanStatus.READY
        assert s1.status == StepStatus.READY
        assert s2.status == StepStatus.PENDING

    def test_ready_steps(self):
        p = Plan(name="x")
        s1 = p.add_step("A")
        s2 = p.add_step("B", depends_on=[s1.step_id])
        p.finalize()
        ready = p.ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == s1.step_id

    def test_dependency_chain(self):
        p = Plan(name="x")
        s1 = p.add_step("A")
        s2 = p.add_step("B", depends_on=[s1.step_id])
        s3 = p.add_step("C", depends_on=[s2.step_id])
        p.finalize()
        assert len(p.ready_steps()) == 1
        s1.complete()
        assert len(p.ready_steps()) == 1
        assert p.ready_steps()[0].step_id == s2.step_id
        s2.complete()
        assert len(p.ready_steps()) == 1
        assert p.ready_steps()[0].step_id == s3.step_id

    def test_progress(self):
        p = Plan(name="x")
        p.add_step("A")
        p.add_step("B")
        p.finalize()
        assert p.progress == 0.0
        p.steps[0].complete()
        assert p.progress == pytest.approx(0.5)
        p.steps[1].complete()
        assert p.progress == 1.0

    def test_all_completed(self):
        p = Plan(name="x")
        p.add_step("A")
        p.finalize()
        assert not p.all_completed()
        p.steps[0].complete()
        assert p.all_completed()

    def test_any_failed(self):
        p = Plan(name="x")
        s = p.add_step("A")
        s.max_retries = 0
        p.finalize()
        s.fail("error")
        assert p.any_failed()

    def test_step_retry(self):
        s = Step(name="retry-me", max_retries=2)
        s.fail("oops")
        assert s.can_retry
        s.reset_for_retry()
        assert s.retry_count == 1
        assert s.status == StepStatus.PENDING
        s.fail("again")
        assert s.can_retry
        s.reset_for_retry()
        assert s.retry_count == 2
        assert not s.can_retry

    def test_step_durations(self):
        s = Step(name="x")
        s.start()
        time.sleep(0.01)
        s.complete()
        assert s.actual_duration > 0
        assert s.completed_at is not None

    def test_skip(self):
        s = Step(name="x")
        s.skip()
        assert s.status == StepStatus.SKIPPED

    def test_to_dict(self):
        p = Plan(name="Test", goal_id="g1")
        p.add_step("A")
        d = p.to_dict()
        assert d["name"] == "Test"
        assert d["goal_id"] == "g1"
        assert d["step_count"] == 1

    def test_cancel_plan(self):
        p = Plan(name="x")
        p.cancel()
        assert p.status == PlanStatus.CANCELLED


# ============================================================
# Execution tests
# ============================================================

class TestExecutionEngine:
    def test_execute_no_actions(self):
        """Steps without registered actions auto-succeed."""
        engine = ExecutionEngine()
        plan = Plan(name="auto")
        plan.add_step("A")
        plan.add_step("B")
        plan.finalize()
        result = engine.execute(plan)
        assert result.success
        assert result.steps_completed == 2
        assert result.steps_failed == 0

    def test_execute_with_actions(self):
        engine = ExecutionEngine()
        call_log = []

        def action_a(step):
            call_log.append(step.name)
            return None  # success

        def action_b(step):
            call_log.append(step.name)
            return None

        engine.register_action("step-a", action_a)
        engine.register_action("step-b", action_b)

        plan = Plan(name="t")
        s1 = plan.add_step("step-a")
        s1.metadata["action"] = "step-a"
        s2 = plan.add_step("step-b", depends_on=[s1.step_id])
        s2.metadata["action"] = "step-b"
        plan.finalize()

        result = engine.execute(plan)
        assert result.success
        assert call_log == ["step-a", "step-b"]

    def test_execute_with_failure(self):
        engine = ExecutionEngine()

        def fail_action(step):
            return "something went wrong"

        engine.register_action("fail-step", fail_action)

        plan = Plan(name="t")
        s = plan.add_step("fail-step")
        s.metadata["action"] = "fail-step"
        s.max_retries = 0
        plan.finalize()

        result = engine.execute(plan)
        assert not result.success
        assert result.steps_failed == 1
        assert len(result.errors) == 1

    def test_execute_with_retry(self):
        engine = ExecutionEngine()
        attempt = {"n": 0}

        def flaky(step):
            attempt["n"] += 1
            if attempt["n"] < 3:
                return "not yet"
            return None

        engine.register_action("flaky", flaky)

        plan = Plan(name="t")
        s = plan.add_step("flaky")
        s.metadata["action"] = "flaky"
        s.max_retries = 3
        plan.finalize()

        result = engine.execute(plan)
        assert result.success
        assert result.retries_used >= 1

    def test_dependency_blocked_on_failure(self):
        engine = ExecutionEngine()

        def fail(step):
            return "nope"

        engine.register_action("bad", fail)

        plan = Plan(name="t")
        s1 = plan.add_step("bad")
        s1.metadata["action"] = "bad"
        s1.max_retries = 0
        s2 = plan.add_step("blocked", depends_on=[s1.step_id])
        plan.finalize()

        result = engine.execute(plan)
        assert not result.success
        assert result.steps_skipped == 1  # s2 skipped

    def test_cannot_execute_draft(self):
        engine = ExecutionEngine()
        plan = Plan(name="draft")
        plan.add_step("A")
        # not finalized
        result = engine.execute(plan)
        assert not result.success

    def test_on_step_callback(self):
        engine = ExecutionEngine()
        steps_seen = []

        plan = Plan(name="t")
        plan.add_step("A")
        plan.add_step("B")
        plan.finalize()

        engine.execute(plan, on_step=lambda s: steps_seen.append(s.name))
        assert steps_seen == ["A", "B"]

    def test_execution_log(self):
        engine = ExecutionEngine()
        plan = Plan(name="t")
        plan.add_step("A")
        plan.finalize()
        engine.execute(plan)
        assert len(engine.execution_log) == 1
        assert engine.execution_log[0]["step_name"] == "A"

    def test_exception_in_action(self):
        engine = ExecutionEngine()

        def boom(step):
            raise RuntimeError("kaboom")

        engine.register_action("boom", boom)
        plan = Plan(name="t")
        s = plan.add_step("boom")
        s.metadata["action"] = "boom"
        s.max_retries = 0
        plan.finalize()

        result = engine.execute(plan)
        assert not result.success
        assert "kaboom" in result.errors[0]


# ============================================================
# Reflection tests
# ============================================================

class TestReflectionEngine:
    def _make_result(self, success=True, completed=3, failed=0, skipped=0,
                     retries=0, duration=1.0, errors=None):
        return ExecutionResult(
            plan_id="p1", success=success,
            steps_completed=completed, steps_failed=failed,
            steps_skipped=skipped, total_duration=duration,
            retries_used=retries, errors=errors or [],
        )

    def test_successful_reflection(self):
        engine = ReflectionEngine()
        plan = Plan(name="t", plan_id="p1")
        plan.add_step("A")
        plan.add_step("B")
        plan.add_step("C")
        plan.finalize()
        for s in plan.steps:
            s.complete()

        result = self._make_result()
        r = engine.reflect(plan, result)
        assert r.success
        assert r.plan_id == "p1"
        assert "completed successfully" in r.summary

    def test_failed_reflection(self):
        engine = ReflectionEngine()
        plan = Plan(name="t")
        s = Step(name="bad", max_retries=0)
        s.fail("nope")
        plan.steps.append(s)

        result = self._make_result(success=False, completed=0, failed=1)
        r = engine.reflect(plan, result)
        assert not r.success
        assert any(l.category == "failure" for l in r.lessons)

    def test_retry_lessons(self):
        engine = ReflectionEngine()
        plan = Plan(name="t")
        s = Step(name="flaky", retry_count=3)
        s.complete()
        plan.steps.append(s)

        result = self._make_result(retries=3)
        r = engine.reflect(plan, result)
        assert any(l.category == "retry" for l in r.lessons)

    def test_timing_lesson(self):
        engine = ReflectionEngine()
        plan = Plan(name="t")
        s = Step(name="slow", estimated_duration=1.0, actual_duration=5.0)
        s.complete()
        plan.steps.append(s)

        result = self._make_result()
        r = engine.reflect(plan, result)
        assert any(l.category == "timing" for l in r.lessons)

    def test_skipped_lesson(self):
        engine = ReflectionEngine()
        plan = Plan(name="t")
        s = Step(name="skipped")
        s.skip()
        plan.steps.append(s)

        result = self._make_result(skipped=1)
        r = engine.reflect(plan, result)
        assert any(l.category == "dependency" for l in r.lessons)

    def test_scores(self):
        engine = ReflectionEngine()
        plan = Plan(name="t")
        plan.add_step("A")
        plan.add_step("B")
        plan.finalize()
        plan.steps[0].complete()
        plan.steps[1].complete()

        result = self._make_result(completed=2)
        r = engine.reflect(plan, result)
        assert "completion_rate" in r.scores
        assert r.scores["completion_rate"] == 1.0

    def test_goal_alignment_strong(self):
        engine = ReflectionEngine()
        plan = Plan(name="t", plan_id="p1")
        plan.add_step("A")
        plan.finalize()
        plan.steps[0].complete()

        goal = Goal(name="g", goal_id="g1")
        goal.add_milestone("m1")
        goal.milestones[0].complete()

        result = self._make_result()
        r = engine.reflect(plan, result, goal)
        assert any(l.category == "alignment" and l.severity == "info" for l in r.lessons)

    def test_goal_alignment_weak(self):
        engine = ReflectionEngine()
        plan = Plan(name="t")
        plan.add_step("A")
        plan.finalize()
        plan.steps[0].complete()

        goal = Goal(name="g")
        # no milestones → progress 0

        result = self._make_result()
        r = engine.reflect(plan, result, goal)
        assert any(l.category == "alignment" and l.severity == "warning" for l in r.lessons)

    def test_get_lessons_by_category(self):
        engine = ReflectionEngine()
        plan = Plan(name="t")
        s = Step(name="flaky", retry_count=1)
        s.complete()
        plan.steps.append(s)

        result = self._make_result(retries=1)
        engine.reflect(plan, result)
        lessons = engine.get_lessons_by_category("retry")
        assert len(lessons) >= 1

    def test_get_lessons_by_severity(self):
        engine = ReflectionEngine()
        plan = Plan(name="t")
        s = Step(name="bad", max_retries=0)
        s.fail("nope")
        plan.steps.append(s)

        result = self._make_result(success=False, failed=1)
        engine.reflect(plan, result)
        critical = engine.get_lessons_by_severity("critical")
        assert len(critical) >= 1


# ============================================================
# Integration: Harbor end-to-end
# ============================================================

class TestHarborIntegration:
    def test_full_workflow(self):
        harbor = ActualizationHarbor()

        # Create goal
        goal = harbor.create_goal("Deploy app", description="Deploy to production")
        goal.add_milestone("Tests pass", target_value=1.0)
        goal.add_milestone("Deployed", target_value=1.0)

        # Create plan
        plan = harbor.create_plan("Deploy plan", goal_id=goal.goal_id)
        s1 = plan.add_step("Run tests")
        s2 = plan.add_step("Build image", depends_on=[s1.step_id])
        s3 = plan.add_step("Deploy", depends_on=[s2.step_id])
        plan.finalize()

        # Execute
        result = harbor.execute(plan)
        assert result.success
        assert result.steps_completed == 3

        # Update milestones
        goal.update_milestone(0, 1.0)
        goal.update_milestone(1, 1.0)
        assert goal.progress == 1.0

        # Reflect
        reflection = harbor.reflect(plan, result, goal)
        assert reflection.success
        assert "completed successfully" in reflection.summary

        # Stats
        stats = harbor.stats()
        assert stats["goals"] == 1
        assert stats["plans"] == 1
        assert stats["reflections"] == 1

    def test_workflow_with_failure_and_retry(self):
        harbor = ActualizationHarbor()

        attempt = {"n": 0}

        def flaky_deploy(step):
            attempt["n"] += 1
            if attempt["n"] < 2:
                return "timeout"
            return None

        harbor.register_action("deploy", flaky_deploy)

        goal = harbor.create_goal("Release v2")
        plan = harbor.create_plan("Release plan", goal_id=goal.goal_id)
        s = plan.add_step("deploy")
        s.metadata["action"] = "deploy"
        s.max_retries = 3
        plan.finalize()

        result = harbor.execute(plan)
        assert result.success
        assert result.retries_used >= 1

        reflection = harbor.reflect(plan, result, goal)
        assert any(l.category == "retry" for l in reflection.lessons)

    def test_decompose_goal(self):
        harbor = ActualizationHarbor()
        parent = harbor.create_goal("Build system")
        sub1 = harbor.decompose_goal(parent.goal_id, "Backend")
        sub2 = harbor.decompose_goal(parent.goal_id, "Frontend")

        assert len(parent.sub_goals) == 2
        assert sub1.parent_id == parent.goal_id
        assert sub2.parent_id == parent.goal_id

    def test_list_goals_with_filter(self):
        harbor = ActualizationHarbor()
        harbor.create_goal("Active 1")
        harbor.create_goal("Active 2")
        g3 = harbor.create_goal("Done")
        g3.complete()

        active = harbor.list_goals(status=GoalStatus.ACTIVE)
        assert len(active) == 2
        completed = harbor.list_goals(status=GoalStatus.COMPLETED)
        assert len(completed) == 1

    def test_list_plans(self):
        harbor = ActualizationHarbor()
        p1 = harbor.create_plan("Plan A")
        p2 = harbor.create_plan("Plan B")
        p2.finalize()

        all_plans = harbor.list_plans()
        assert len(all_plans) == 2
        ready = harbor.list_plans(status=PlanStatus.READY)
        assert len(ready) == 1

    def test_get_goal_and_plan(self):
        harbor = ActualizationHarbor()
        g = harbor.create_goal("Find me")
        p = harbor.create_plan("Find me too")

        assert harbor.get_goal(g.goal_id) is g
        assert harbor.get_plan(p.plan_id) is p
        assert harbor.get_goal("nonexistent") is None
        assert harbor.get_plan("nonexistent") is None
