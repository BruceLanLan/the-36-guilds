"""Template engine: loading, validation, and customization of org templates."""

import copy
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schema import AgentDef, OrgTemplate, ReviewGate, Stage, TaskFlowStep

PRESETS_DIR = Path(__file__).parent / "presets"


class TemplateEngine:
    """Loads, validates, and customizes organizational templates."""

    def __init__(self, presets_dir: Path = PRESETS_DIR):
        self.presets_dir = presets_dir

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_templates(self) -> List[Dict[str, str]]:
        """Return metadata for every available preset template."""
        templates = []
        for f in sorted(self.presets_dir.glob("*.yaml")):
            try:
                raw = yaml.safe_load(f.read_text(encoding="utf-8"))
                merged = self._merge_raw(raw)
                templates.append({
                    "file": f.stem,
                    "name": merged.get("name", f.stem),
                    "name_en": merged.get("name_en", ""),
                    "icon": merged.get("icon", ""),
                    "description": merged.get("description", ""),
                    "category": merged.get("category", ""),
                    "agent_count": len(merged.get("agents", [])),
                    "stage_count": len(merged.get("stages", [])),
                })
            except Exception as e:
                templates.append({"file": f.stem, "error": str(e)})
        return templates

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_template(self, name: str) -> OrgTemplate:
        """Load a template by filename (without .yaml extension)."""
        path = self.presets_dir / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {path}")
        return self.load_from_file(path)

    def load_from_file(self, path: Path) -> OrgTemplate:
        """Load a template from an arbitrary YAML file."""
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        merged = self._merge_raw(raw)
        return self._parse_template(merged)

    @staticmethod
    def _merge_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Merge top-level keys with the nested 'template' dict.

        Supports both flat and nested YAML layouts:
          - Flat:   {name, agents, stages, ...}
          - Nested: {template: {name, ...}, agents: [...], stages: [...], ...}
        """
        base = dict(raw.get("template", {}))
        for key in ("stages", "agents", "permissions", "task_flow",
                     "review_gates", "metadata"):
            if key in raw and key not in base:
                base[key] = raw[key]
        if not base:
            base = raw
        return base

    def _parse_template(self, data: Dict[str, Any]) -> OrgTemplate:
        stages = [Stage(**s) for s in data.get("stages", [])]

        agents = []
        for a in data.get("agents", []):
            agents.append(AgentDef(
                id=a["id"],
                name=a["name"],
                icon=a.get("icon", "🤖"),
                role=a.get("role", ""),
                stage=a.get("stage", ""),
                description=a.get("description", ""),
                responsibilities=a.get("responsibilities", []),
                soul=a.get("soul", ""),
                model=a.get("model", "default"),
                skills=a.get("skills", []),
            ))

        permissions = data.get("permissions", {})

        task_flow = []
        for step in data.get("task_flow", []):
            task_flow.append(TaskFlowStep(
                from_agent=step["from"],
                to_agent=step["to"],
                action=step.get("action", ""),
                can_reject=step.get("can_reject", False),
                reject_to=step.get("reject_to"),
            ))

        review_gates = []
        for gate in data.get("review_gates", []):
            review_gates.append(ReviewGate(
                stage=gate["stage"],
                reviewer=gate["reviewer"],
                criteria=gate.get("criteria", []),
                can_reject=gate.get("can_reject", True),
                reject_to=gate.get("reject_to"),
            ))

        return OrgTemplate(
            name=data.get("name", ""),
            name_en=data.get("name_en", ""),
            description=data.get("description", ""),
            icon=data.get("icon", ""),
            version=data.get("version", "1.0"),
            category=data.get("category", ""),
            stages=stages,
            agents=agents,
            permissions=permissions,
            task_flow=task_flow,
            review_gates=review_gates,
            metadata=data.get("metadata", {}),
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, template: OrgTemplate) -> List[str]:
        """Validate a loaded template. Returns error messages (empty = valid)."""
        return template.validate()

    # ------------------------------------------------------------------
    # Customization helpers
    # ------------------------------------------------------------------

    def add_agent(self, template: OrgTemplate, agent: AgentDef,
                  permissions_to: Optional[List[str]] = None,
                  permissions_from: Optional[List[str]] = None) -> OrgTemplate:
        """Return a copy of *template* with a new agent appended."""
        tpl = copy.deepcopy(template)
        tpl.agents.append(agent)
        tpl.permissions[agent.id] = permissions_to or []
        if permissions_from:
            for src in permissions_from:
                if src in tpl.permissions:
                    tpl.permissions[src].append(agent.id)
        return tpl

    def remove_agent(self, template: OrgTemplate, agent_id: str) -> OrgTemplate:
        """Return a copy with an agent removed (and permissions cleaned up)."""
        tpl = copy.deepcopy(template)
        tpl.agents = [a for a in tpl.agents if a.id != agent_id]
        tpl.permissions.pop(agent_id, None)
        for key in tpl.permissions:
            tpl.permissions[key] = [t for t in tpl.permissions[key] if t != agent_id]
        tpl.task_flow = [
            s for s in tpl.task_flow
            if s.from_agent != agent_id and s.to_agent != agent_id
        ]
        tpl.review_gates = [g for g in tpl.review_gates if g.reviewer != agent_id]
        return tpl

    def set_model(self, template: OrgTemplate, agent_id: str, model: str) -> OrgTemplate:
        """Change the model for a specific agent."""
        tpl = copy.deepcopy(template)
        agent = tpl.get_agent(agent_id)
        if agent:
            agent.model = model
        return tpl

    def merge_templates(self, base: OrgTemplate, extension: OrgTemplate) -> OrgTemplate:
        """Merge extension agents/permissions into base template."""
        tpl = copy.deepcopy(base)
        existing_ids = set(tpl.get_agent_ids())
        for agent in extension.agents:
            if agent.id not in existing_ids:
                tpl.agents.append(copy.deepcopy(agent))
        for agent_id, targets in extension.permissions.items():
            if agent_id not in tpl.permissions:
                tpl.permissions[agent_id] = list(targets)
            else:
                for t in targets:
                    if t not in tpl.permissions[agent_id]:
                        tpl.permissions[agent_id].append(t)
        tpl.task_flow.extend(copy.deepcopy(extension.task_flow))
        tpl.review_gates.extend(copy.deepcopy(extension.review_gates))
        return tpl

    def export_yaml(self, template: OrgTemplate, path: Path):
        """Export a (possibly customized) template back to YAML."""
        data = {
            "template": {
                "name": template.name,
                "name_en": template.name_en,
                "description": template.description,
                "icon": template.icon,
                "version": template.version,
                "category": template.category,
                "metadata": template.metadata,
                "stages": [
                    {"id": s.id, "name": s.name, "description": s.description}
                    for s in template.stages
                ],
                "agents": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "icon": a.icon,
                        "role": a.role,
                        "stage": a.stage,
                        "description": a.description,
                        "responsibilities": a.responsibilities,
                        "soul": a.soul,
                        "model": a.model,
                        "skills": a.skills,
                    }
                    for a in template.agents
                ],
                "permissions": template.permissions,
                "task_flow": [
                    {
                        "from": s.from_agent,
                        "to": s.to_agent,
                        "action": s.action,
                        "can_reject": s.can_reject,
                        **({"reject_to": s.reject_to} if s.reject_to else {}),
                    }
                    for s in template.task_flow
                ],
                "review_gates": [
                    {
                        "stage": g.stage,
                        "reviewer": g.reviewer,
                        "criteria": g.criteria,
                        "can_reject": g.can_reject,
                        **({"reject_to": g.reject_to} if g.reject_to else {}),
                    }
                    for g in template.review_gates
                ],
            }
        }
        path.write_text(
            yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
