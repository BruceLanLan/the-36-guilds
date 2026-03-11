"""Data models for organizational templates."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class Stage:
    """A stage in the task processing pipeline."""
    id: str
    name: str
    description: str


@dataclass
class AgentDef:
    """Definition of a single agent within an organizational template."""
    id: str
    name: str
    icon: str
    role: str
    stage: str
    description: str
    responsibilities: List[str]
    soul: str
    model: str = "default"
    skills: List[str] = field(default_factory=list)


@dataclass
class TaskFlowStep:
    """A step in the task flow pipeline."""
    from_agent: Union[str, List[str]]
    to_agent: Union[str, List[str]]
    action: str
    can_reject: bool = False
    reject_to: Optional[str] = None


@dataclass
class ReviewGate:
    """A mandatory review checkpoint in the pipeline."""
    stage: str
    reviewer: str
    criteria: List[str]
    can_reject: bool = True
    reject_to: Optional[str] = None


@dataclass
class OrgTemplate:
    """Complete organizational template definition."""
    name: str
    name_en: str
    description: str
    icon: str
    version: str
    category: str
    stages: List[Stage]
    agents: List[AgentDef]
    permissions: Dict[str, List[str]]
    task_flow: List[TaskFlowStep]
    review_gates: List[ReviewGate]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_agent(self, agent_id: str) -> Optional[AgentDef]:
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        return None

    def get_agents_at_stage(self, stage_id: str) -> List[AgentDef]:
        return [a for a in self.agents if a.stage == stage_id]

    def get_agent_ids(self) -> List[str]:
        return [a.id for a in self.agents]

    def validate(self) -> List[str]:
        """Validate template consistency. Returns list of error messages."""
        errors = []
        agent_ids = set(self.get_agent_ids())
        stage_ids = {s.id for s in self.stages}

        if len(agent_ids) != len(self.agents):
            errors.append("Duplicate agent IDs detected")

        for agent in self.agents:
            if agent.stage not in stage_ids:
                errors.append(f"Agent '{agent.id}' references unknown stage '{agent.stage}'")

        for agent_id, targets in self.permissions.items():
            if agent_id not in agent_ids:
                errors.append(f"Permission references unknown agent '{agent_id}'")
            for target in targets:
                if target not in agent_ids:
                    errors.append(f"Permission target '{target}' is unknown (from '{agent_id}')")

        for step in self.task_flow:
            sources = [step.from_agent] if isinstance(step.from_agent, str) else step.from_agent
            targets = [step.to_agent] if isinstance(step.to_agent, str) else step.to_agent
            for s in sources:
                if s not in agent_ids:
                    errors.append(f"Task flow references unknown agent '{s}'")
            for t in targets:
                if t not in agent_ids:
                    errors.append(f"Task flow references unknown agent '{t}'")

        for gate in self.review_gates:
            if gate.reviewer not in agent_ids:
                errors.append(f"Review gate references unknown reviewer '{gate.reviewer}'")
            if gate.reject_to and gate.reject_to not in agent_ids:
                errors.append(f"Review gate reject_to references unknown agent '{gate.reject_to}'")

        return errors
