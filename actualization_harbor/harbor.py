"""Harbor — main entry point for goal actualization with planning, execution, and reflection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

from .execution import ExecutionEngine, ExecutionResult, StepAction
from .goal import Goal, GoalStatus, Milestone
from .plan import Plan, PlanStatus, Step, StepStatus
from .reflection import Reflection, ReflectionEngine


class FlowState(Enum):
    IDLE = "idle"
    ENTERING = "entering"
    TRAINING = "training"
    INTEGRATING = "integrating"
    DEPARTING = "departing"


@dataclass
class Adaptation:
    """An adaptation made for a specific agent type."""
    agent_type: str
    parameters: Dict[str, float] = field(default_factory=dict)
    notes: str = ""


@dataclass
class AgentProfile:
    """Profile of an agent visiting the harbor."""
    agent_id: str
    model_type: str = "unknown"
    context_window: int = 0
    capabilities: List[str] = field(default_factory=list)
    preferred_tempo: float = 1.0
    last_visit: float = 0.0
    visits: int = 0
    adaptations: List[Adaptation] = field(default_factory=list)


class ActualizationHarbor:
    """Safe harbor for agent goal actualization.

    Provides planning, execution, and reflection for agents pursuing goals.

    Usage:
        harbor = ActualizationHarbor()

        # Register an agent
        harbor.register("agent-1", model_type="llm-7b")

        # Create a goal
        goal = harbor.create_goal("Build API", description="REST API for users")

        # Create a plan for the goal
        plan = harbor.create_plan("API Plan", goal_id=goal.goal_id)
        plan.add_step("Design routes")
        plan.add_step("Implement handlers", depends_on=[plan.steps[0].step_id])
        plan.add_step("Write tests", depends_on=[plan.steps[1].step_id])
        plan.finalize()

        # Execute
        result = harbor.execute(plan)

        # Reflect
        reflection = harbor.reflect(plan, result, goal)
        print(reflection.summary)
    """

    def __init__(self):
        # Agent management (legacy)
        self.profiles: Dict[str, AgentProfile] = {}
        self.flow_states: Dict[str, FlowState] = {}
        self.history: List[dict] = []

        # Goal/Plan/Execution/Reflection
        self.goals: Dict[str, Goal] = {}
        self.plans: Dict[str, Plan] = {}
        self.execution_engine = ExecutionEngine()
        self.reflection_engine = ReflectionEngine()

    # ---- Agent management (legacy API preserved) ----

    def register(self, agent_id: str, **kwargs) -> AgentProfile:
        profile = AgentProfile(agent_id=agent_id, **kwargs)
        self.profiles[agent_id] = profile
        self.flow_states[agent_id] = FlowState.IDLE
        return profile

    def enter(self, agent_id: str) -> FlowState:
        if agent_id not in self.profiles:
            self.register(agent_id)
        self.flow_states[agent_id] = FlowState.ENTERING
        profile = self.profiles[agent_id]
        profile.visits += 1
        profile.last_visit = time.time()
        return FlowState.ENTERING

    def assess(self, agent_id: str) -> List[Adaptation]:
        profile = self.profiles.get(agent_id)
        if not profile:
            return []
        adaptations = []
        if profile.context_window > 0:
            batch_size = min(5, max(1, profile.context_window // 1000))
            adaptations.append(Adaptation(
                agent_type=profile.model_type,
                parameters={"batch_size": float(batch_size)},
                notes=f"context={profile.context_window}, batch={batch_size}",
            ))
        if profile.preferred_tempo > 0:
            interval = 1.0 / profile.preferred_tempo
            adaptations.append(Adaptation(
                agent_type=profile.model_type,
                parameters={"tick_interval": interval},
            ))
        if profile.capabilities:
            difficulty = min(1.0, len(profile.capabilities) / 10.0)
            adaptations.append(Adaptation(
                agent_type=profile.model_type,
                parameters={"difficulty": difficulty},
                notes=f"{len(profile.capabilities)} capabilities detected",
            ))
        profile.adaptations.extend(adaptations)
        return adaptations

    def train(self, agent_id: str) -> bool:
        if self.flow_states.get(agent_id) != FlowState.ENTERING:
            return False
        self.flow_states[agent_id] = FlowState.TRAINING
        self.history.append({
            "agent_id": agent_id,
            "action": "train",
            "timestamp": time.time(),
            "visits": self.profiles[agent_id].visits,
        })
        return True

    def integrate(self, agent_id: str) -> bool:
        if self.flow_states.get(agent_id) != FlowState.TRAINING:
            return False
        self.flow_states[agent_id] = FlowState.INTEGRATING
        return True

    def depart(self, agent_id: str) -> FlowState:
        self.flow_states[agent_id] = FlowState.DEPARTING
        return FlowState.DEPARTING

    def state(self, agent_id: str) -> FlowState:
        return self.flow_states.get(agent_id, FlowState.IDLE)

    def docked_agents(self) -> List[str]:
        active = {FlowState.ENTERING, FlowState.TRAINING, FlowState.INTEGRATING}
        return [aid for aid, s in self.flow_states.items() if s in active]

    def stats(self) -> dict:
        return {
            "registered": len(self.profiles),
            "docked": len(self.docked_agents()),
            "total_visits": sum(p.visits for p in self.profiles.values()),
            "total_adaptations": sum(len(p.adaptations) for p in self.profiles.values()),
            "goals": len(self.goals),
            "plans": len(self.plans),
            "reflections": len(self.reflection_engine.reflections),
        }

    # ---- Goal management ----

    def create_goal(self, name: str, description: str = "",
                    priority: int = 0, tags: Optional[List[str]] = None,
                    deadline: Optional[float] = None) -> Goal:
        goal = Goal(name=name, description=description, priority=priority,
                    tags=tags or [], deadline=deadline)
        goal.activate()
        self.goals[goal.goal_id] = goal
        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        return self.goals.get(goal_id)

    def list_goals(self, status: Optional[GoalStatus] = None) -> List[Goal]:
        goals = list(self.goals.values())
        if status:
            goals = [g for g in goals if g.status == status]
        return sorted(goals, key=lambda g: g.priority, reverse=True)

    def decompose_goal(self, parent_id: str, sub_name: str, **kwargs) -> Goal:
        """Create a sub-goal under a parent goal."""
        parent = self.goals.get(parent_id)
        if not parent:
            raise ValueError(f"Goal {parent_id} not found")
        sub = Goal(name=sub_name, parent_id=parent_id, **kwargs)
        sub.activate()
        parent.sub_goals.append(sub.goal_id)
        self.goals[sub.goal_id] = sub
        return sub

    # ---- Plan management ----

    def create_plan(self, name: str, description: str = "",
                    goal_id: Optional[str] = None) -> Plan:
        plan = Plan(name=name, description=description, goal_id=goal_id)
        self.plans[plan.plan_id] = plan
        return plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self.plans.get(plan_id)

    def list_plans(self, status: Optional[PlanStatus] = None) -> List[Plan]:
        plans = list(self.plans.values())
        if status:
            plans = [p for p in plans if p.status == status]
        return plans

    # ---- Execution ----

    def register_action(self, action_name: str, fn: StepAction) -> None:
        self.execution_engine.register_action(action_name, fn)

    def execute(self, plan: Plan,
                on_step: Optional[Callable[[Step], None]] = None) -> ExecutionResult:
        return self.execution_engine.execute(plan, on_step=on_step)

    # ---- Reflection ----

    def reflect(self, plan: Plan, result: ExecutionResult,
                goal: Optional[Goal] = None) -> Reflection:
        return self.reflection_engine.reflect(plan, result, goal)
