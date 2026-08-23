# actualization-harbor

**A safe harbor for agent goal actualization** — planning, execution, and reflection. Pure Python, zero dependencies.

<p align="center">
  <img src="assets/images/hero-harbor.jpg" width="680" alt="A chart-room lamp throwing amber light on a hand-drawn course line to safe anchorage — the plan, already underway in the dark">
</p>

## What This Gives You

- **Goal management** — define goals with milestones, track progress, decompose into sub-goals
- **Planning** — create plans with ordered steps and dependency graphs (DAG)
- **Execution** — run plans with automatic retry, dependency resolution, and failure handling
- **Reflection** — analyze outcomes, compute scores, extract lessons by category/severity
- **Agent profiles** — registration and adaptation for backward compatibility

## Installation

```bash
pip install actualization-harbor
```

## Quick Start

```python
from actualization_harbor import ActualizationHarbor

harbor = ActualizationHarbor()

goal = harbor.create_goal("Deploy to production", priority=5)
goal.add_milestone("All tests pass", target_value=1.0)
goal.add_milestone("Staging validated", target_value=1.0)

plan = harbor.create_plan("Deploy plan", goal_id=goal.goal_id)
s1 = plan.add_step("Run test suite", estimated_duration=60.0)
s2 = plan.add_step("Build Docker image", depends_on=[s1.step_id])
s3 = plan.add_step("Push to staging", depends_on=[s2.step_id])
plan.finalize()

result = harbor.execute(plan)
print(f"Success: {result.success}, {result.steps_completed}/{len(plan.steps)} steps")
```

## Testing

```bash
pip install -e .
pytest
```

## How It Fits

Goal execution layer for the SuperInstance agent fleet. Works with `plato-training` rooms and `a2a-protocol` for multi-agent coordination.

## License

MIT
