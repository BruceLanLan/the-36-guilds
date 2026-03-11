"""
Template Renderer — generates all artifacts needed to run a multi-agent setup:
  - SOUL.md files (agent personality / workflow rules)
  - agents.yaml config
  - openclaw.json permission entries
  - install_agents.sh setup script
"""

import json
from datetime import datetime
from pathlib import Path

import yaml

from .schema import OrgTemplate


class TemplateRenderer:
    """Render an OrgTemplate into on-disk artifacts."""

    def __init__(self, template: OrgTemplate, output_dir: Path):
        self.template = template
        self.output_dir = output_dir

    def render_all(self):
        """Generate every artifact in one call."""
        self.render_soul_files()
        self.render_agents_config()
        self.render_openclaw_config()
        self.render_install_script()
        self.render_permission_matrix()
        self.render_flow_diagram()

    # ------------------------------------------------------------------
    # SOUL.md
    # ------------------------------------------------------------------

    def render_soul_files(self):
        """Create agents/<id>/SOUL.md for each agent."""
        for agent in self.template.agents:
            agent_dir = self.output_dir / "agent_workspaces" / agent.id
            agent_dir.mkdir(parents=True, exist_ok=True)
            soul_path = agent_dir / "SOUL.md"

            can_send_to = self.template.permissions.get(agent.id, [])
            receives_from = [
                aid for aid, targets in self.template.permissions.items()
                if agent.id in targets
            ]

            content = self._build_soul(agent, can_send_to, receives_from)
            soul_path.write_text(content, encoding="utf-8")

    def _build_soul(self, agent, can_send_to, receives_from) -> str:
        responsibilities_md = "\n".join(f"- {r}" for r in agent.responsibilities)

        send_labels = []
        for a in can_send_to:
            t = self.template.get_agent(a)
            if t:
                send_labels.append(f"{t.icon} {t.name} (`@{a}`)")
        recv_labels = []
        for a in receives_from:
            t = self.template.get_agent(a)
            if t:
                recv_labels.append(f"{t.icon} {t.name} (`@{a}`)")

        send_list = ", ".join(send_labels) or "无"
        recv_list = ", ".join(recv_labels) or "无"

        is_entry = (agent.id == self.template.entry_point)
        entry_agent = self.template.get_entry_agent()

        routing = self._build_routing_instructions(agent, can_send_to, receives_from, is_entry)

        parts = [
            f"# {agent.icon} {agent.name} — {agent.role}",
            "",
            f"> 组织架构：{self.template.icon} {self.template.name}（{self.template.name_en}）",
        ]

        if is_entry:
            parts.append(f"> **🎯 入口 Agent** — 用户通过 Telegram / Lark 直接与你对话")

        parts.extend([
            "",
            "## 角色定位",
            agent.description,
            "",
            "## 核心职责",
            responsibilities_md,
            "",
            "## 通讯权限（OpenClaw）",
            "",
            "使用 `@agent_id` 格式给其他 Agent 发送消息。",
            "",
            f"- **可发送消息给**：{send_list}",
            f"- **可接收消息来自**：{recv_list}",
            "",
            "---",
            "",
            agent.soul.strip(),
            "",
            "---",
            "",
            routing,
            "",
        ])
        return "\n".join(parts)

    def _build_routing_instructions(self, agent, can_send_to, receives_from, is_entry) -> str:
        """Generate OpenClaw-specific routing instructions for this agent."""
        lines = ["# OpenClaw 协作规则"]
        lines.append("")
        lines.append("你是 OpenClaw 多 Agent 协作系统中的一员。请严格遵守以下规则：")
        lines.append("")

        if is_entry:
            lines.append("## 你是入口 Agent")
            lines.append("")
            lines.append("- 用户通过 Telegram / Lark / Signal 向你发送消息")
            lines.append("- **简单问题**：直接回复用户")
            lines.append("- **复杂任务**：整理需求后，使用 `@agent_id` 转发给下游 Agent")
            lines.append("- 当收到最终结果时，**整理成用户友好的格式直接回复**（用户看不到内部流转）")
            lines.append("")

        lines.append("## 消息转发规则")
        lines.append("")

        outgoing = self._get_outgoing_flows(agent.id)
        incoming = self._get_incoming_flows(agent.id)

        if outgoing:
            lines.append("当你需要将工作传递给下游时：")
            for step in outgoing:
                to_ids = [step.to_agent] if isinstance(step.to_agent, str) else step.to_agent
                for to_id in to_ids:
                    to_agent = self.template.get_agent(to_id)
                    if to_agent:
                        lines.append(f"- **{step.action}** → 发消息给 `@{to_id}`（{to_agent.icon} {to_agent.name}）")
            lines.append("")

        if incoming:
            lines.append("当你收到以下来源的消息时：")
            for step in incoming:
                from_ids = [step.from_agent] if isinstance(step.from_agent, str) else step.from_agent
                for from_id in from_ids:
                    from_agent = self.template.get_agent(from_id)
                    if from_agent:
                        lines.append(f"- 来自 `@{from_id}`（{from_agent.icon} {from_agent.name}）→ {step.action}")
            lines.append("")

        reject_flows = [s for s in outgoing if s.can_reject]
        if reject_flows:
            lines.append("## 审核封驳")
            lines.append("")
            for step in reject_flows:
                if step.reject_to:
                    reject_agent = self.template.get_agent(step.reject_to)
                    if reject_agent:
                        lines.append(f"- 如果不合格，发消息给 `@{step.reject_to}`（{reject_agent.icon} {reject_agent.name}）并说明打回原因")
            lines.append("")

        lines.append("## 消息格式")
        lines.append("")
        lines.append("给其他 Agent 发消息时，使用以下格式：")
        lines.append("```")
        lines.append(f"@目标agent_id")
        lines.append(f"【任务类型】：xxx")
        lines.append(f"【内容】：xxx")
        lines.append("```")

        return "\n".join(lines)

    def _get_outgoing_flows(self, agent_id):
        """Get task_flow steps where this agent is the sender."""
        results = []
        for step in self.template.task_flow:
            sources = [step.from_agent] if isinstance(step.from_agent, str) else step.from_agent
            if agent_id in sources:
                results.append(step)
        return results

    def _get_incoming_flows(self, agent_id):
        """Get task_flow steps where this agent is the receiver."""
        results = []
        for step in self.template.task_flow:
            targets = [step.to_agent] if isinstance(step.to_agent, str) else step.to_agent
            if agent_id in targets:
                results.append(step)
        return results

    # ------------------------------------------------------------------
    # agents.yaml
    # ------------------------------------------------------------------

    def render_agents_config(self):
        """Generate config/agents.yaml from the template."""
        config_dir = self.output_dir / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        agents_cfg = {}
        for agent in self.template.agents:
            agents_cfg[agent.id] = {
                "name": agent.name,
                "role": agent.role,
                "stage": agent.stage,
                "model": agent.model,
                "skills": agent.skills,
                "permissions": self.template.permissions.get(agent.id, []),
            }

        data = {
            "template": {
                "name": self.template.name,
                "name_en": self.template.name_en,
                "version": self.template.version,
                "category": self.template.category,
            },
            "system": {
                "heartbeat_interval": 900,
                "workspace": "./agent_workspaces",
            },
            "stages": [
                {"id": s.id, "name": s.name, "description": s.description}
                for s in self.template.stages
            ],
            "agents": agents_cfg,
        }

        path = config_dir / "agents.yaml"
        path.write_text(
            yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # openclaw.json
    # ------------------------------------------------------------------

    def render_openclaw_config(self) -> dict:
        """Generate openclaw_agents.json with agent registrations and permissions."""
        agents_list = []
        for agent in self.template.agents:
            agents_list.append({
                "id": agent.id,
                "name": f"{agent.icon} {agent.name}",
                "role": agent.role,
                "workspace": f"./agent_workspaces/{agent.id}",
                "model": agent.model,
                "allowed_contacts": self.template.permissions.get(agent.id, []),
            })

        data = {
            "_comment": f"Auto-generated by The 36 Guilds from template: {self.template.name} ({self.template.name_en})",
            "_generated_at": datetime.now().isoformat(),
            "agents": agents_list,
        }

        path = self.output_dir / "openclaw_agents.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    # ------------------------------------------------------------------
    # install script
    # ------------------------------------------------------------------

    def render_install_script(self):
        """Generate install_agents.sh that sets up OpenClaw workspaces."""
        lines = [
            "#!/usr/bin/env bash",
            f'# Auto-generated by The 36 Guilds',
            f'# Template: {self.template.icon} {self.template.name} ({self.template.name_en})',
            f'# Generated at: {datetime.now().isoformat()}',
            'set -euo pipefail',
            '',
            'echo "============================================"',
            f'echo "{self.template.icon} Installing: {self.template.name} ({self.template.name_en})"',
            f'echo "  Agents: {len(self.template.agents)}"',
            f'echo "  Stages: {len(self.template.stages)}"',
            'echo "============================================"',
            '',
            'if ! command -v openclaw &>/dev/null; then',
            '    echo "⚠️  openclaw CLI not found. Skipping agent registration."',
            '    echo "   Workspaces and SOUL.md files will still be created."',
            '    SKIP_REGISTER=1',
            'else',
            '    SKIP_REGISTER=0',
            'fi',
            '',
            'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"',
            'WORKSPACE_DIR="${SCRIPT_DIR}/agent_workspaces"',
            '',
            'echo ""',
            'echo "📁 Creating agent workspaces..."',
        ]

        for agent in self.template.agents:
            lines.append(f'mkdir -p "${{WORKSPACE_DIR}}/{agent.id}"')
            lines.append(f'echo "  ✅ {agent.icon} {agent.name} ({agent.id})"')

        lines.extend([
            '',
            'echo ""',
            'echo "📜 SOUL.md files are in place."',
            '',
            'if [ "$SKIP_REGISTER" -eq 0 ]; then',
            '    echo ""',
            '    echo "🔧 Registering agents with OpenClaw..."',
        ])

        for agent in self.template.agents:
            contacts = self.template.permissions.get(agent.id, [])
            contacts_str = ",".join(contacts) if contacts else ""
            lines.append(
                f'    openclaw agent create --id {agent.id} '
                f'--name "{agent.icon} {agent.name}" '
                f'--workspace "${{WORKSPACE_DIR}}/{agent.id}" '
                f'--contacts "{contacts_str}" 2>/dev/null || '
                f'echo "    ⚠️  Agent {agent.id} may already exist, skipping."'
            )

        lines.extend([
            '',
            '    echo ""',
            '    echo "🔄 Restarting OpenClaw gateway..."',
            '    openclaw gateway restart 2>/dev/null || echo "    ⚠️  Gateway restart skipped."',
            'fi',
            '',
            'echo ""',
            'echo "============================================"',
            f'echo "✅ {self.template.icon} {self.template.name} setup complete!"',
            'echo ""',
            'echo "Next steps:"',
            'echo "  1. Review SOUL.md files in agent_workspaces/"',
            'echo "  2. Customize agent models in config/agents.yaml"',
            'echo "  3. Start your system"',
            'echo "============================================"',
        ])

        path = self.output_dir / "install_agents.sh"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        path.chmod(0o755)

    # ------------------------------------------------------------------
    # Permission matrix (markdown)
    # ------------------------------------------------------------------

    def render_permission_matrix(self):
        """Generate a markdown permission matrix for reference."""
        agent_ids = self.template.get_agent_ids()
        agent_names = {a.id: f"{a.icon}{a.name}" for a in self.template.agents}

        lines = [
            f"# {self.template.icon} {self.template.name} — 权限矩阵",
            "",
            "| From ↓ \\ To → |" + "|".join(f" {agent_names[a]} " for a in agent_ids) + "|",
            "|" + "|".join("---" for _ in range(len(agent_ids) + 1)) + "|",
        ]

        for src in agent_ids:
            targets = set(self.template.permissions.get(src, []))
            cells = []
            for dst in agent_ids:
                if src == dst:
                    cells.append(" — ")
                elif dst in targets:
                    cells.append(" ✅ ")
                else:
                    cells.append("    ")
            lines.append(f"| **{agent_names[src]}** |" + "|".join(cells) + "|")

        lines.extend(["", "---", f"_Generated by The 36 Guilds · template v{self.template.version}_"])

        docs_dir = self.output_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "permission_matrix.md").write_text("\n".join(lines), encoding="utf-8")

    # ------------------------------------------------------------------
    # Flow diagram (text-based)
    # ------------------------------------------------------------------

    def render_flow_diagram(self):
        """Generate a text-based task flow diagram."""
        lines = [
            f"# {self.template.icon} {self.template.name} — 任务流转图",
            "",
            "## 阶段概览",
        ]

        for stage in self.template.stages:
            agents_at = self.template.get_agents_at_stage(stage.id)
            agent_str = ", ".join(f"{a.icon}{a.name}" for a in agents_at)
            lines.append(f"  {stage.name} → [{agent_str}]")

        lines.extend(["", "## 流转步骤", ""])

        for i, step in enumerate(self.template.task_flow, 1):
            from_str = step.from_agent if isinstance(step.from_agent, str) else " + ".join(step.from_agent)
            to_str = step.to_agent if isinstance(step.to_agent, str) else " + ".join(step.to_agent)

            from_agent = self.template.get_agent(from_str) if isinstance(step.from_agent, str) else None
            to_agent = self.template.get_agent(to_str) if isinstance(step.to_agent, str) else None

            from_label = f"{from_agent.icon}{from_agent.name}" if from_agent else from_str
            to_label = f"{to_agent.icon}{to_agent.name}" if to_agent else to_str

            arrow = "→✅→" if not step.can_reject else "→🚫→"
            lines.append(f"  {i}. {from_label} {arrow} {to_label}")
            lines.append(f"     {step.action}")
            if step.can_reject and step.reject_to:
                reject_agent = self.template.get_agent(step.reject_to)
                reject_label = f"{reject_agent.icon}{reject_agent.name}" if reject_agent else step.reject_to
                lines.append(f"     (可打回至: {reject_label})")
            lines.append("")

        lines.extend(["## 审核关卡", ""])
        for gate in self.template.review_gates:
            reviewer = self.template.get_agent(gate.reviewer)
            reviewer_label = f"{reviewer.icon}{reviewer.name}" if reviewer else gate.reviewer
            lines.append(f"  🔍 {gate.stage} 阶段 — 审核人: {reviewer_label}")
            for criterion in gate.criteria:
                lines.append(f"     - {criterion}")
            if gate.reject_to:
                reject_agent = self.template.get_agent(gate.reject_to)
                reject_label = f"{reject_agent.icon}{reject_agent.name}" if reject_agent else gate.reject_to
                lines.append(f"     封驳打回至: {reject_label}")
            lines.append("")

        docs_dir = self.output_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "task_flow.md").write_text("\n".join(lines), encoding="utf-8")
