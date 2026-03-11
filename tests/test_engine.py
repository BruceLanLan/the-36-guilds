"""Tests for the template engine and renderer."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from guilds.engine import TemplateEngine
from guilds.renderer import TemplateRenderer


def test_list_templates():
    engine = TemplateEngine()
    templates = engine.list_templates()
    assert len(templates) >= 4, f"Expected at least 4 templates, got {len(templates)}"
    for tpl in templates:
        assert "error" not in tpl, f"Template {tpl['file']} has error: {tpl.get('error')}"
        assert tpl["agent_count"] > 0, f"Template {tpl['file']} has no agents"
        assert tpl["stage_count"] > 0, f"Template {tpl['file']} has no stages"
    print(f"  ✓ list_templates: {len(templates)} templates found")


def test_load_all_templates():
    engine = TemplateEngine()
    template_names = ["imperial_court", "it_company", "investment_firm", "quant_trading"]
    for name in template_names:
        tpl = engine.load_template(name)
        assert tpl.name, f"{name}: missing name"
        assert len(tpl.agents) > 0, f"{name}: no agents"
        assert len(tpl.stages) > 0, f"{name}: no stages"
        assert len(tpl.permissions) > 0, f"{name}: no permissions"
        assert len(tpl.task_flow) > 0, f"{name}: no task_flow"
        print(f"  ✓ load {name}: {len(tpl.agents)} agents, {len(tpl.stages)} stages")


def test_validate_all_templates():
    engine = TemplateEngine()
    template_names = ["imperial_court", "it_company", "investment_firm", "quant_trading"]
    for name in template_names:
        tpl = engine.load_template(name)
        errors = tpl.validate()
        assert not errors, f"{name} validation failed: {errors}"
        print(f"  ✓ validate {name}: OK")


def test_remove_agent():
    engine = TemplateEngine()
    tpl = engine.load_template("it_company")
    original_count = len(tpl.agents)

    modified = engine.remove_agent(tpl, "devops")
    assert len(modified.agents) == original_count - 1
    assert "devops" not in modified.get_agent_ids()
    assert "devops" not in modified.permissions
    for targets in modified.permissions.values():
        assert "devops" not in targets
    print(f"  ✓ remove_agent: {original_count} → {len(modified.agents)} agents")


def test_set_model():
    engine = TemplateEngine()
    tpl = engine.load_template("it_company")

    modified = engine.set_model(tpl, "cto", "gpt-4o")
    assert modified.get_agent("cto").model == "gpt-4o"
    assert tpl.get_agent("cto").model == "default"  # original unchanged
    print("  ✓ set_model: OK")


def test_render_all():
    engine = TemplateEngine()
    tpl = engine.load_template("it_company")

    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir)
        renderer = TemplateRenderer(tpl, output)
        renderer.render_all()

        for agent in tpl.agents:
            soul = output / "agent_workspaces" / agent.id / "SOUL.md"
            assert soul.exists(), f"Missing SOUL.md for {agent.id}"
            content = soul.read_text()
            assert agent.name in content
            assert "通讯权限" in content

        assert (output / "config" / "agents.yaml").exists()
        assert (output / "openclaw_agents.json").exists()
        assert (output / "install_agents.sh").exists()
        assert (output / "docs" / "permission_matrix.md").exists()
        assert (output / "docs" / "task_flow.md").exists()

        print(f"  ✓ render_all: {len(tpl.agents)} SOUL.md + config + docs generated")


def test_export_and_reimport():
    engine = TemplateEngine()
    tpl = engine.load_template("quant_trading")

    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = Path(tmpdir) / "exported.yaml"
        engine.export_yaml(tpl, export_path)
        assert export_path.exists()

        reimported = engine.load_from_file(export_path)
        assert reimported.name == tpl.name
        assert len(reimported.agents) == len(tpl.agents)
        assert len(reimported.stages) == len(tpl.stages)
        print("  ✓ export_and_reimport: round-trip OK")


if __name__ == "__main__":
    print("\n三十六行 · The 36 Guilds — Test Suite\n")

    test_list_templates()
    test_load_all_templates()
    test_validate_all_templates()
    test_remove_agent()
    test_set_model()
    test_render_all()
    test_export_and_reimport()

    print("\n✅ All tests passed!\n")
