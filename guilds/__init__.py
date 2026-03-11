"""
三十六行 · The 36 Guilds
Multi-Agent Organizational Template System

行行出状元 — Every guild has its champion.
Define organizational structures in YAML, generate multi-agent systems.
"""

__version__ = "0.1.0"

from .schema import AgentDef, Stage, TaskFlowStep, ReviewGate, OrgTemplate
from .engine import TemplateEngine
from .renderer import TemplateRenderer

__all__ = [
    "AgentDef",
    "Stage",
    "TaskFlowStep",
    "ReviewGate",
    "OrgTemplate",
    "TemplateEngine",
    "TemplateRenderer",
]
