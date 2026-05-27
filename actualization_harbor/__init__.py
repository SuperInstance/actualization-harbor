"""actualization-harbor — A safe harbor for agent goal actualization.

Provides planning, execution, and reflection for agents pursuing goals.
The harbor doesn't care what kind of ship you are —
it adjusts the channel depth to fit your hull.
"""

__version__ = "0.2.0"

from .goal import Goal, GoalStatus, Milestone
from .plan import Plan, PlanStatus, Step, StepStatus
from .execution import ExecutionEngine, ExecutionResult
from .reflection import Reflection, ReflectionEngine, Lesson
from .harbor import ActualizationHarbor, AgentProfile, FlowState, Adaptation

__all__ = [
    # Core
    "ActualizationHarbor",
    # Goal
    "Goal", "GoalStatus", "Milestone",
    # Plan
    "Plan", "PlanStatus", "Step", "StepStatus",
    # Execution
    "ExecutionEngine", "ExecutionResult",
    # Reflection
    "Reflection", "ReflectionEngine", "Lesson",
    # Legacy agent
    "AgentProfile", "FlowState", "Adaptation",
]
