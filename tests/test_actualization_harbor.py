"""Tests for actualization-harbor."""
import pytest
from actualization_harbor import ActualizationHarbor, FlowState


def test_register_and_enter():
    h = ActualizationHarbor()
    h.register("agent-1", model_type="llm-7b", context_window=4096)
    state = h.enter("agent-1")
    assert state == FlowState.ENTERING
    assert h.profiles["agent-1"].visits == 1


def test_full_cycle():
    h = ActualizationHarbor()
    h.register("a")
    h.enter("a")
    h.train("a")
    h.integrate("a")
    h.depart("a")
    assert h.state("a") == FlowState.DEPARTING


def test_assess_adaptations():
    h = ActualizationHarbor()
    h.register("smart", model_type="llm-70b", context_window=8192,
               capabilities=["code", "math", "reasoning", "writing"])
    h.enter("smart")
    adaptations = h.assess("smart")
    assert len(adaptations) >= 2
    params = {p: v for a in adaptations for p, v in a.parameters.items()}
    assert "batch_size" in params


def test_cannot_train_without_enter():
    h = ActualizationHarbor()
    h.register("a")
    assert not h.train("a")  # must enter first


def test_docked_agents():
    h = ActualizationHarbor()
    h.register("a")
    h.register("b")
    h.enter("a")
    h.enter("b")
    h.train("a")
    assert len(h.docked_agents()) == 2


def test_auto_register_on_enter():
    h = ActualizationHarbor()
    h.enter("unknown-agent")
    assert "unknown-agent" in h.profiles
    assert h.profiles["unknown-agent"].visits == 1
