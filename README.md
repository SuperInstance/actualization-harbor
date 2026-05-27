# Actualization Harbor

**A safe harbor for agent goal actualization — planning, execution, and reflection.**

The Harbor provides infrastructure for agents to define goals, create plans with dependencies, execute those plans with retry/rollback, and reflect on outcomes to extract lessons. It doesn't care what kind of ship you are — it adjusts the channel depth to fit your hull.

---

## Features

- **Goal management** — define goals with milestones, track progress, decompose into sub-goals
- **Planning** — create plans with ordered steps and dependency graphs
- **Execution** — run plans with automatic retry, dependency resolution, and failure handling
- **Reflection** — analyze outcomes, compute scores, extract lessons by category/severity
- **Agent profiles** — legacy agent registration and adaptation preserved for backward compatibility
- **Zero dependencies** — uses only dataclasses, typing, and stdlib (pytest for tests)

## Installation

```bash
pip install actualization-harbor
```

## Quick Start

```python
from actualization_harbor import ActualizationHarbor

harbor = ActualizationHarbor()

# Create a goal with milestones
goal = harbor.create_goal("Deploy to production", priority=5)
goal.add_milestone("All tests pass", target_value=1.0)
goal.add_milestone("Staging validated", target_value=1.0)
goal.add_milestone("Production live", target_value=1.0)

# Create a plan with dependencies
plan = harbor.create_plan("Deploy plan", goal_id=goal.goal_id)
s1 = plan.add_step("Run test suite", estimated_duration=60.0)
s2 = plan.add_step("Build Docker image", depends_on=[s1.step_id], estimated_duration=120.0)
s3 = plan.add_step("Push to staging", depends_on=[s2.step_id])
s4 = plan.add_step("Smoke test staging", depends_on=[s3.step_id])
s5 = plan.add_step("Promote to production", depends_on=[s4.step_id])
plan.finalize()

# Execute the plan
result = harbor.execute(plan)
print(f"Success: {result.success}")
print(f"Completed: {result.steps_completed}/{len(plan.steps)} steps in {result.total_duration:.2f}s")

# Update goal milestones
for i in range(len(goal.milestones)):
    goal.update_milestone(i, 1.0)

# Reflect on the execution
reflection = harbor.reflect(plan, result, goal)
print(reflection.summary)
for lesson in reflection.lessons:
    print(f"  [{lesson.severity}] {lesson.title}")
```

## Registering Custom Actions

Steps execute registered actions by name. If no action is registered, the step auto-succeeds (useful for modeling/prototyping).

```python
def fetch_data(step):
    # Do real work here
    if error:
        return "Failed to fetch"  # return error string
    return None  # None = success

harbor.register_action("fetch", fetch_data)

# In your plan step:
step = plan.add_step("fetch")
step.metadata["action"] = "fetch"
```

## Retries and Failure Handling

Steps can retry automatically:

```python
step = plan.add_step("flaky-api-call", max_retries=5)
step.metadata["action"] = "api-call"
```

When a step fails permanently, downstream dependent steps are skipped and the plan is marked as failed.

## Goal Decomposition

Break large goals into sub-goals:

```python
parent = harbor.create_goal("Build microservices")
backend = harbor.decompose_goal(parent.goal_id, "Backend service")
frontend = harbor.decompose_goal(parent.goal_id, "Frontend app")
```

## Reflection and Lessons

After execution, the reflection engine analyzes:

- **Retry patterns** — which steps needed retries
- **Failures** — what failed and why
- **Timing** — steps that exceeded estimated duration
- **Skipped steps** — cascade failures from dependencies
- **Goal alignment** — whether plan completion moved the goal forward

```python
reflection = harbor.reflect(plan, result, goal)

# Scores: completion_rate, failure_rate, timing_accuracy, reliability, throughput
print(reflection.scores)

# Filter lessons
critical = engine.get_lessons_by_severity("critical")
timing = engine.get_lessons_by_category("timing")
```

## Legacy Agent API

The original agent registration API is preserved:

```python
harbor.register("agent-1", model_type="llm-7b", context_window=4096)
harbor.enter("agent-1")
adaptations = harbor.assess("agent-1")
harbor.train("agent-1")
harbor.integrate("agent-1")
harbor.depart("agent-1")
```

## Development

```bash
git clone https://github.com/SuperInstance/actualization-harbor
cd actualization-harbor
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## How It Fits

- **[actualization-harbor](https://github.com/SuperInstance/actualization-harbor)** — planning, execution, reflection (this)
- **[agent-bootcamp](https://github.com/SuperInstance/agent-bootcamp)** — generates skills the Harbor certifies
- **[arena-combat-analyst-1](https://github.com/SuperInstance/arena-combat-analyst-1)** — competition tracked by the Harbor
- **[agent-skills](https://github.com/SuperInstance/agent-skills)** — skills the Harbor serves
- **[ai-character-sdk](https://github.com/SuperInstance/ai-character-sdk)** — characters that train in the Harbor

## License

MIT
