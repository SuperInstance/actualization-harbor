# actualization-harbor

Agent-agnostic training harbor. The harbor doesn't care what kind of ship you are — it adjusts the channel depth to fit your hull.

Any agent can dock, get assessed, receive adapted training flow, and depart more capable. Detects model type, context window, capabilities, and preferred tempo. Generates adaptations automatically.

## Usage

```python
from actualization_harbor import ActualizationHarbor

harbor = ActualizationHarbor()
harbor.register("jetson-agent", model_type="llm-7b", context_window=4096,
                capabilities=["edge", "cuda"])

harbor.enter("jetson-agent")
adaptations = harbor.assess("jetson-agent")
harbor.train("jetson-agent")
harbor.integrate("jetson-agent")
harbor.depart("jetson-agent")
```

Zero deps. `pip install actualization-harbor`
