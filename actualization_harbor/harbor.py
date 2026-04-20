"""Agent-agnostic training harbor."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


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
    preferred_tempo: float = 1.0  # tasks per cycle
    last_visit: float = 0.0
    visits: int = 0
    adaptations: List[Adaptation] = field(default_factory=list)


class ActualizationHarbor:
    """Agent-agnostic training harbor.
    
    Any agent can dock, get assessed, receive adapted training,
    and depart more capable. The harbor detects what kind of agent
    you are and adjusts accordingly.
    
    Usage:
        harbor = ActualizationHarbor()
        profile = harbor.register("agent-x", model_type="llm-7b", context_window=4096)
        state = harbor.enter("agent-x")
        adaptations = harbor.assess("agent-x")
        harbor.train("agent-x")
        harbor.depart("agent-x")
    """
    
    def __init__(self):
        self.profiles: Dict[str, AgentProfile] = {}
        self.flow_states: Dict[str, FlowState] = {}
        self.history: List[dict] = []
    
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
        """Assess agent and determine adaptations."""
        profile = self.profiles.get(agent_id)
        if not profile:
            return []
        
        adaptations = []
        
        # Context-based adaptation
        if profile.context_window > 0:
            batch_size = min(5, max(1, profile.context_window // 1000))
            adaptations.append(Adaptation(
                agent_type=profile.model_type,
                parameters={"batch_size": float(batch_size)},
                notes=f"context={profile.context_window}, batch={batch_size}",
            ))
        
        # Tempo adaptation
        if profile.preferred_tempo > 0:
            interval = 1.0 / profile.preferred_tempo
            adaptations.append(Adaptation(
                agent_type=profile.model_type,
                parameters={"tick_interval": interval},
            ))
        
        # Capability-based curriculum
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
        }
