#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三十六行 · The 36 Guilds — Setup CLI

Interactive tool for selecting, customizing, and deploying organizational
templates for multi-agent systems.

Usage:
    python3 setup_guilds.py                          # Interactive mode
    python3 setup_guilds.py --list                   # List available templates
    python3 setup_guilds.py --template it_company    # Direct selection
    python3 setup_guilds.py --template it_company --output ./my_setup
    python3 setup_guilds.py --custom path/to/my.yaml # Custom template
"""

import argparse
import sys
from pathlib import Path

from guilds.engine import TemplateEngine
from guilds.renderer import TemplateRenderer


def print_banner():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  三十六行 · The 36 Guilds                               ║")
    print("║  行行出状元 — Every guild has its champion.              ║")
    print("║                                                          ║")
    print("║  选择组织架构模版，一键生成多Agent协作系统                  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()


def print_template_list(templates):
    print("  可用模版 (Available Templates):")
    print("  ─────────────────────────────────────────────────────")
    for i, tpl in enumerate(templates, 1):
        if "error" in tpl:
            print(f"  {i}. ⚠️  {tpl['file']} — 加载失败: {tpl['error']}")
        else:
            print(f"  {i}. {tpl['icon']}  {tpl['name']} ({tpl['name_en']})")
            print(f"      {tpl['description'][:60]}")
            print(f"      Agents: {tpl['agent_count']} | Stages: {tpl['stage_count']}")
            print(f"      ➜ --template {tpl['file']}")
        print()


def print_template_detail(template):
    print(f"\n  {template.icon} {template.name} — {template.name_en}")
    print(f"  {template.description}")
    print()

    print("  📋 任务流水线 (Pipeline):")
    for stage in template.stages:
        agents_at = template.get_agents_at_stage(stage.id)
        agent_str = ", ".join(f"{a.icon}{a.name}" for a in agents_at)
        print(f"    → {stage.name}: [{agent_str}]")
    print()

    print("  🤖 Agent 列表:")
    for agent in template.agents:
        print(f"    {agent.icon} {agent.name:12s} — {agent.description[:50]}")
    print()

    if template.review_gates:
        print("  🔍 审核关卡:")
        for gate in template.review_gates:
            reviewer = template.get_agent(gate.reviewer)
            name = f"{reviewer.icon}{reviewer.name}" if reviewer else gate.reviewer
            print(f"    ✋ {gate.stage} 阶段 → 审核人: {name} (可封驳打回)")
        print()


def interactive_customize(engine, template):
    """Allow user to customize a template interactively."""
    while True:
        print("  自定义选项 (Customization):")
        print("  1. 查看权限矩阵")
        print("  2. 删除某个 Agent")
        print("  3. 修改 Agent 模型")
        print("  4. 确认生成 →")
        print("  5. 返回模版列表")
        print()

        choice = input("  选择 [1-5]: ").strip()

        if choice == "1":
            print("\n  权限矩阵 (Permission Matrix):")
            for src in template.get_agent_ids():
                targets = template.permissions.get(src, [])
                agent = template.get_agent(src)
                label = f"{agent.icon}{agent.name}" if agent else src
                target_labels = []
                for t in targets:
                    ta = template.get_agent(t)
                    target_labels.append(f"{ta.icon}{ta.name}" if ta else t)
                print(f"    {label:16s} → {', '.join(target_labels) or '(无)'}")
            print()

        elif choice == "2":
            print("\n  当前 Agents:")
            for i, agent in enumerate(template.agents, 1):
                print(f"    {i}. {agent.icon} {agent.name} ({agent.id})")
            idx = input("  要删除的编号 (0=取消): ").strip()
            if idx.isdigit() and 0 < int(idx) <= len(template.agents):
                agent_id = template.agents[int(idx) - 1].id
                template = engine.remove_agent(template, agent_id)
                print(f"  ✅ 已删除 {agent_id}")
            print()

        elif choice == "3":
            print("\n  当前 Agents 及模型:")
            for i, agent in enumerate(template.agents, 1):
                print(f"    {i}. {agent.icon} {agent.name} — model: {agent.model}")
            idx = input("  要修改的编号 (0=取消): ").strip()
            if idx.isdigit() and 0 < int(idx) <= len(template.agents):
                agent_id = template.agents[int(idx) - 1].id
                new_model = input("  新模型名称: ").strip()
                if new_model:
                    template = engine.set_model(template, agent_id, new_model)
                    print(f"  ✅ {agent_id} 模型已改为 {new_model}")
            print()

        elif choice == "4":
            return template

        elif choice == "5":
            return None

    return template


def generate(template, output_dir: Path):
    """Generate all artifacts from a template."""
    errors = template.validate()
    if errors:
        print("  ⚠️  模版验证发现问题:")
        for err in errors:
            print(f"    - {err}")
        if not sys.stdin.isatty():
            print("  ❌ 非交互模式下跳过有错误的模版")
            return False
        confirm = input("  仍然继续生成? [y/N]: ").strip().lower()
        if confirm != "y":
            return False

    output_dir.mkdir(parents=True, exist_ok=True)
    renderer = TemplateRenderer(template, output_dir)
    renderer.render_all()

    print()
    print("  ✅ 生成完成！文件列表:")
    print(f"    📁 {output_dir}/")

    for agent in template.agents:
        soul_path = output_dir / "agent_workspaces" / agent.id / "SOUL.md"
        if soul_path.exists():
            print(f"      ├── agent_workspaces/{agent.id}/SOUL.md")

    for name in ["config/agents.yaml", "openclaw_agents.json", "install_agents.sh"]:
        if (output_dir / name).exists():
            print(f"      ├── {name}")

    docs_dir = output_dir / "docs"
    if docs_dir.exists():
        for f in sorted(docs_dir.glob("*.md")):
            print(f"      ├── docs/{f.name}")

    print()
    print("  下一步:")
    print("    1. 查看并定制 agent_workspaces/ 中的 SOUL.md 文件")
    print("    2. 编辑 config/agents.yaml 调整模型和参数")
    print("    3. 运行 bash install_agents.sh 注册到 OpenClaw")
    print()
    return True


def main():
    parser = argparse.ArgumentParser(
        description="三十六行 · The 36 Guilds — Multi-Agent Template System"
    )
    parser.add_argument("--list", action="store_true", help="列出所有可用模版")
    parser.add_argument("--template", type=str, help="直接指定模版名称 (如 it_company)")
    parser.add_argument("--custom", type=str, help="使用自定义模版 YAML 文件路径")
    parser.add_argument("--output", type=str, default=".", help="输出目录 (默认当前目录)")
    args = parser.parse_args()

    engine = TemplateEngine()
    output_dir = Path(args.output)

    if args.list:
        print_banner()
        print_template_list(engine.list_templates())
        return

    if args.custom:
        custom_path = Path(args.custom)
        if not custom_path.exists():
            print(f"  ❌ 文件不存在: {custom_path}")
            sys.exit(1)
        template = engine.load_from_file(custom_path)
        print_banner()
        print_template_detail(template)
        generate(template, output_dir)
        return

    if args.template:
        try:
            template = engine.load_template(args.template)
        except FileNotFoundError:
            print(f"  ❌ 模版不存在: {args.template}")
            print("  可用模版:")
            for tpl in engine.list_templates():
                print(f"    - {tpl['file']}")
            sys.exit(1)
        print_banner()
        print_template_detail(template)
        generate(template, output_dir)
        return

    # Interactive mode
    print_banner()
    templates = engine.list_templates()

    while True:
        print_template_list(templates)

        valid = [t for t in templates if "error" not in t]
        print(f"  {len(valid) + 1}. 📁  加载自定义模版 YAML 文件...")
        print(f"  {len(valid) + 2}. 🚪  退出")
        print()

        choice = input(f"  选择模版 [1-{len(valid) + 2}]: ").strip()
        if not choice.isdigit():
            continue

        idx = int(choice)

        if idx == len(valid) + 2:
            print("  👋 再见!")
            return

        if idx == len(valid) + 1:
            custom_path = input("  YAML 文件路径: ").strip()
            if not Path(custom_path).exists():
                print(f"  ❌ 文件不存在: {custom_path}")
                continue
            template = engine.load_from_file(Path(custom_path))
        elif 1 <= idx <= len(valid):
            template = engine.load_template(valid[idx - 1]["file"])
        else:
            continue

        print_template_detail(template)

        print("  操作选项:")
        print("  1. ✅ 使用默认配置直接生成")
        print("  2. ✏️  自定义后生成")
        print("  3. ↩️  返回模版列表")
        print()

        action = input("  选择 [1-3]: ").strip()

        if action == "1":
            out = input(f"  输出目录 [{output_dir}]: ").strip()
            if out:
                output_dir = Path(out)
            generate(template, output_dir)
            return

        elif action == "2":
            result = interactive_customize(engine, template)
            if result:
                out = input(f"  输出目录 [{output_dir}]: ").strip()
                if out:
                    output_dir = Path(out)
                generate(result, output_dir)
                return


if __name__ == "__main__":
    main()
