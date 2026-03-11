#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三十六行 · The 36 Guilds — OpenClaw One-Click Installer

Detects your OpenClaw installation, generates SOUL.md files for all agents,
registers them in openclaw.json, sets up bindings, and restarts the gateway.

Usage:
    python3 install_openclaw.py --template it_company
    python3 install_openclaw.py --template quant_trading --tg-account quantbot
    python3 install_openclaw.py --list
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_DIR))

from guilds.engine import TemplateEngine
from guilds.renderer import TemplateRenderer

OPENCLAW_DIR = Path.home() / ".openclaw"
OPENCLAW_JSON = OPENCLAW_DIR / "openclaw.json"

engine = TemplateEngine()


def detect_openclaw():
    """Check if OpenClaw is installed and return config path."""
    if not OPENCLAW_DIR.exists():
        return None
    if not OPENCLAW_JSON.exists():
        return None
    return OPENCLAW_JSON


def load_openclaw_config():
    """Load openclaw.json, returns dict."""
    text = OPENCLAW_JSON.read_text(encoding="utf-8")
    return json.loads(text)


def backup_openclaw_config():
    """Create a timestamped backup of openclaw.json."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = OPENCLAW_DIR / f"openclaw.json.bak.guilds-{ts}"
    shutil.copy2(OPENCLAW_JSON, backup)
    return backup


def save_openclaw_config(config):
    """Write config back to openclaw.json."""
    text = json.dumps(config, ensure_ascii=False, indent=2)
    OPENCLAW_JSON.write_text(text, encoding="utf-8")


def get_existing_agent_ids(config):
    """Get list of already registered agent IDs."""
    agents_section = config.get("agents", {})
    agent_list = agents_section.get("list", [])
    return {a.get("id") for a in agent_list if a.get("id")}


def get_existing_bindings(config):
    """Get list of existing binding accountIds."""
    return {
        b["match"]["accountId"]
        for b in config.get("bindings", [])
        if "match" in b and "accountId" in b["match"]
    }


def get_default_model(config):
    """Get the default model from OpenClaw config."""
    agents_section = config.get("agents", {})
    defaults = agents_section.get("defaults", {})
    model_config = defaults.get("model", {})
    return model_config.get("primary", "default")


def build_openclaw_soul(template, agent):
    """Build a SOUL.md in OpenClaw's native format for a single agent."""
    is_entry = (agent.id == template.entry_point)

    can_send_to = template.permissions.get(agent.id, [])
    receives_from = [
        aid for aid, targets in template.permissions.items()
        if agent.id in targets
    ]

    parts = []
    parts.append(f"# SOUL.md — {agent.icon} {agent.name}")
    parts.append("")
    parts.append(f"_{template.icon} {template.name} · {template.name_en}_")
    parts.append("")

    if is_entry:
        parts.append("> **🎯 你是入口 Agent** — 用户直接和你对话。简单问题直接回答，复杂任务走流水线。")
        parts.append("")

    parts.append("## 身份与职责")
    parts.append("")
    parts.append(f"**角色**：{agent.role}")
    parts.append(f"**定位**：{agent.description}")
    parts.append("")
    parts.append("**核心职责**：")
    for r in agent.responsibilities:
        parts.append(f"- {r}")
    parts.append("")

    parts.append("## 协作网络")
    parts.append("")
    send_labels = []
    for a_id in can_send_to:
        t = template.get_agent(a_id)
        if t:
            send_labels.append(f"`@{a_id}`（{t.icon} {t.name}）")
    recv_labels = []
    for a_id in receives_from:
        t = template.get_agent(a_id)
        if t:
            recv_labels.append(f"`@{a_id}`（{t.icon} {t.name}）")

    parts.append(f"- **可发消息给**：{', '.join(send_labels) or '无'}")
    parts.append(f"- **可接收来自**：{', '.join(recv_labels) or '无'}")
    parts.append("")

    parts.append("---")
    parts.append("")
    parts.append(agent.soul.strip())
    parts.append("")

    parts.append("---")
    parts.append("")
    parts.append("## 协作规则")
    parts.append("")

    if is_entry:
        parts.append("你是入口 Agent。用户通过消息平台直接和你对话。")
        parts.append("- **简单问题** → 直接回复")
        parts.append("- **复杂任务** → 整理需求后用 `@agent_id` 转发给下游")
        parts.append("- 收到最终结果后 → **整理成用户友好的格式回复**（用户看不到内部流转）")
        parts.append("")

    outgoing = _get_outgoing_flows(template, agent.id)
    incoming = _get_incoming_flows(template, agent.id)

    if outgoing:
        parts.append("**发出任务**：")
        for step in outgoing:
            to_ids = [step.to_agent] if isinstance(step.to_agent, str) else step.to_agent
            for to_id in to_ids:
                to_a = template.get_agent(to_id)
                if to_a:
                    parts.append(f"- {step.action} → `@{to_id}`（{to_a.icon} {to_a.name}）")
        parts.append("")

    if incoming:
        parts.append("**接收任务**：")
        for step in incoming:
            from_ids = [step.from_agent] if isinstance(step.from_agent, str) else step.from_agent
            for from_id in from_ids:
                from_a = template.get_agent(from_id)
                if from_a:
                    parts.append(f"- 来自 `@{from_id}`（{from_a.icon} {from_a.name}）→ {step.action}")
        parts.append("")

    reject_flows = [s for s in outgoing if s.can_reject and s.reject_to]
    if reject_flows:
        parts.append("**审核封驳**：")
        for step in reject_flows:
            reject_a = template.get_agent(step.reject_to)
            if reject_a:
                parts.append(f"- 不合格 → `@{step.reject_to}`（{reject_a.icon} {reject_a.name}）说明打回原因")
        parts.append("")

    parts.append("**消息格式**：给其他 Agent 发消息时：")
    parts.append("```")
    parts.append("@目标agent_id")
    parts.append("【任务】：xxx")
    parts.append("【内容】：xxx")
    parts.append("```")
    parts.append("")

    parts.append("## 行为规范")
    parts.append("")
    parts.append("- 只和权限列表中的 Agent 通讯，不要越级")
    parts.append("- 每次收到任务先确认理解，再执行")
    parts.append("- 完成后明确告知结果和状态")
    parts.append("- 遇到问题及时上报，不要卡住")
    parts.append("")

    return "\n".join(parts)


def _get_outgoing_flows(template, agent_id):
    results = []
    for step in template.task_flow:
        sources = [step.from_agent] if isinstance(step.from_agent, str) else step.from_agent
        if agent_id in sources:
            results.append(step)
    return results


def _get_incoming_flows(template, agent_id):
    results = []
    for step in template.task_flow:
        targets = [step.to_agent] if isinstance(step.to_agent, str) else step.to_agent
        if agent_id in targets:
            results.append(step)
    return results


def install_template(template, tg_account=None, model_override=None):
    """Install a template into OpenClaw. The main function."""

    print()
    print(f"  {template.icon} 安装 {template.name}（{template.name_en}）到 OpenClaw")
    print(f"  {'─' * 50}")

    config = load_openclaw_config()
    existing_ids = get_existing_agent_ids(config)
    default_model = model_override or get_default_model(config)
    entry_agent = template.get_entry_agent()

    conflicts = [a.id for a in template.agents if a.id in existing_ids]
    if conflicts:
        print(f"\n  ⚠️  以下 Agent ID 已存在：{', '.join(conflicts)}")
        print(f"  将跳过已存在的 Agent，只安装新的。")
        print()

    # --- 1. Backup ---
    backup = backup_openclaw_config()
    print(f"  ✅ 已备份 openclaw.json → {backup.name}")

    # --- 2. Create workspaces + SOUL.md ---
    installed_agents = []
    for agent in template.agents:
        if agent.id in existing_ids:
            print(f"  ⏭️  跳过 {agent.icon} {agent.name}（{agent.id}）— 已存在")
            continue

        workspace = OPENCLAW_DIR / f"workspace-guilds-{agent.id}"
        workspace.mkdir(parents=True, exist_ok=True)

        soul_content = build_openclaw_soul(template, agent)
        (workspace / "SOUL.md").write_text(soul_content, encoding="utf-8")

        agents_md = OPENCLAW_DIR / "workspace" / "AGENTS.md"
        if agents_md.exists():
            shutil.copy2(agents_md, workspace / "AGENTS.md")

        installed_agents.append({
            "id": agent.id,
            "name": f"{agent.icon} {agent.name}",
            "workspace": str(workspace),
            "model": default_model,
        })
        print(f"  ✅ {agent.icon} {agent.name}（{agent.id}）→ {workspace.name}/")

    if not installed_agents:
        print("\n  ℹ️  没有新 Agent 需要安装。")
        return

    # --- 3. Register agents in openclaw.json ---
    agents_section = config.setdefault("agents", {})
    agent_list = agents_section.setdefault("list", [])

    for agent_info in installed_agents:
        agent_list.append({
            "id": agent_info["id"],
            "name": agent_info["name"],
            "workspace": agent_info["workspace"],
            "model": agent_info["model"],
        })

    print(f"\n  ✅ {len(installed_agents)} 个 Agent 注册到 openclaw.json")

    # --- 4. Set up binding for entry agent ---
    if entry_agent and entry_agent.id not in existing_ids:
        bindings = config.setdefault("bindings", [])
        used_accounts = get_existing_bindings(config)

        if tg_account:
            bind_account = tg_account
        else:
            candidates = ["default", "bot2", "bot3", "guilds"]
            bind_account = None
            for c in candidates:
                if c not in used_accounts:
                    bind_account = c
                    break
            if not bind_account:
                bind_account = f"guilds-{template.entry_point}"

        bindings.append({
            "agentId": entry_agent.id,
            "match": {
                "channel": "telegram",
                "accountId": bind_account,
            }
        })
        print(f"  ✅ 入口 Agent {entry_agent.icon} {entry_agent.name} 绑定到 Telegram 账号 '{bind_account}'")

        if bind_account not in used_accounts and bind_account not in ("bot1", "default"):
            print(f"\n  ⚠️  Telegram 账号 '{bind_account}' 可能需要配置 Bot Token：")
            print(f"     openclaw channels add --channel telegram --account {bind_account} --token YOUR_BOT_TOKEN")
    else:
        bind_account = None

    # --- 5. Save config ---
    save_openclaw_config(config)
    print(f"\n  ✅ openclaw.json 已更新")

    # --- 6. Restart gateway ---
    print(f"\n  🔄 重启 OpenClaw Gateway...")
    try:
        result = subprocess.run(
            ["openclaw", "gateway", "restart"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            print(f"  ✅ Gateway 已重启")
        else:
            print(f"  ⚠️  Gateway 重启返回码 {result.returncode}")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[:5]:
                    print(f"     {line}")
    except FileNotFoundError:
        print(f"  ⚠️  未找到 openclaw 命令，请手动重启：openclaw gateway restart")
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  重启超时，请手动检查：openclaw gateway restart")

    # --- 7. Summary ---
    print()
    print(f"  {'═' * 50}")
    print(f"  ✅ 安装完成！{template.icon} {template.name}")
    print(f"  {'═' * 50}")
    print()
    print(f"  📊 安装了 {len(installed_agents)} 个 Agent")
    print(f"  🎯 入口 Agent：{entry_agent.icon} {entry_agent.name}（{entry_agent.id}）")
    if bind_account:
        print(f"  📱 Telegram 绑定：{bind_account}")
    print()
    print(f"  下一步：")
    if bind_account and bind_account not in ("bot1", "default"):
        print(f"  1. 配置 Telegram Bot Token（如果还没配置）：")
        print(f"     openclaw channels add --channel telegram --account {bind_account} --token YOUR_TOKEN")
        print(f"  2. 给 Telegram Bot 发消息测试")
    else:
        print(f"  1. 给 Telegram Bot 发消息测试")
    print()
    print(f"  也可以用命令行测试：")
    print(f"  openclaw agent --agent {entry_agent.id} --message \"帮我设计一个用户注册系统\"")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="三十六行 · The 36 Guilds — OpenClaw 一键安装"
    )
    parser.add_argument("--list", action="store_true", help="列出可用模版")
    parser.add_argument("--template", type=str, help="模版名称 (如 it_company)")
    parser.add_argument("--tg-account", type=str, help="绑定到的 Telegram 账号 ID")
    parser.add_argument("--model", type=str, help="覆盖所有 Agent 的模型")
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  三十六行 · The 36 Guilds — OpenClaw Installer           ║")
    print("╚══════════════════════════════════════════════════════════╝")

    if args.list:
        templates = engine.list_templates()
        print()
        for t in templates:
            if "error" not in t:
                print(f"  {t['icon']}  {t['name']}（{t['name_en']}）")
                print(f"     Agents: {t['agent_count']} | ➜ --template {t['file']}")
                print()
        return

    # Detect OpenClaw
    oc_path = detect_openclaw()
    if not oc_path:
        print()
        print("  ❌ 未检测到 OpenClaw 安装")
        print(f"     找不到 {OPENCLAW_DIR} 或 {OPENCLAW_JSON}")
        print()
        print("  请先安装 OpenClaw：https://openclaw.ai")
        sys.exit(1)

    print(f"\n  ✅ 检测到 OpenClaw：{oc_path}")

    if not args.template:
        print("\n  请指定模版：")
        templates = engine.list_templates()
        for t in templates:
            if "error" not in t:
                print(f"    python3 install_openclaw.py --template {t['file']}")
        print()
        sys.exit(0)

    try:
        template = engine.load_template(args.template)
    except FileNotFoundError:
        print(f"\n  ❌ 模版不存在：{args.template}")
        print("  可用模版：")
        for t in engine.list_templates():
            if "error" not in t:
                print(f"    --template {t['file']}")
        sys.exit(1)

    errors = template.validate()
    if errors:
        print(f"\n  ❌ 模版验证失败：")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)

    install_template(template, tg_account=args.tg_account, model_override=args.model)


if __name__ == "__main__":
    main()
