#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三十六行 · The 36 Guilds — Web UI Server

Zero-dependency web server (Python stdlib only).
Serves the dashboard UI and provides JSON API for template management.

Usage:
    python3 server.py              # Start on port 7892
    python3 server.py --port 8080  # Custom port
"""

import argparse
import json
import os
import sys
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PROJECT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_DIR))

from guilds.engine import TemplateEngine
from guilds.renderer import TemplateRenderer

engine = TemplateEngine()


def template_to_dict(tpl):
    """Serialize an OrgTemplate to a JSON-safe dict."""
    entry = tpl.get_entry_agent()
    return {
        "name": tpl.name,
        "name_en": tpl.name_en,
        "description": tpl.description,
        "icon": tpl.icon,
        "version": tpl.version,
        "category": tpl.category,
        "entry_point": tpl.entry_point,
        "entry_agent": {
            "id": entry.id, "name": entry.name, "icon": entry.icon,
            "role": entry.role, "description": entry.description,
        } if entry else None,
        "metadata": tpl.metadata,
        "stages": [
            {"id": s.id, "name": s.name, "description": s.description}
            for s in tpl.stages
        ],
        "agents": [
            {
                "id": a.id, "name": a.name, "icon": a.icon,
                "role": a.role, "stage": a.stage,
                "description": a.description,
                "responsibilities": a.responsibilities,
                "model": a.model,
            }
            for a in tpl.agents
        ],
        "permissions": tpl.permissions,
        "task_flow": [
            {
                "from": s.from_agent, "to": s.to_agent,
                "action": s.action, "can_reject": s.can_reject,
                "reject_to": s.reject_to,
            }
            for s in tpl.task_flow
        ],
        "review_gates": [
            {
                "stage": g.stage, "reviewer": g.reviewer,
                "criteria": g.criteria, "can_reject": g.can_reject,
                "reject_to": g.reject_to,
            }
            for g in tpl.review_gates
        ],
    }


class GuildsHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the Guilds dashboard."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_DIR / "ui"), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)

        if path == "" or path == "/index.html":
            self._serve_file(PROJECT_DIR / "ui" / "index.html", "text/html")
        elif path == "/api/templates":
            self._json_response(engine.list_templates())
        elif path.startswith("/api/templates/"):
            name = path.split("/")[-1]
            try:
                tpl = engine.load_template(name)
                self._json_response({"file": name, **template_to_dict(tpl)})
            except FileNotFoundError:
                self._json_response({"error": f"Template '{name}' not found"}, 404)
        elif path == "/api/preview":
            self._safe_handle(self._handle_preview, qs)
        elif path == "/api/verify":
            self._safe_handle(self._handle_verify, qs)
        else:
            super().do_GET()

    def _handle_preview(self, qs):
        """Read and return a generated file's content."""
        output_dir = qs.get("dir", [""])[0]
        file_path = qs.get("file", [""])[0]
        if not output_dir or not file_path:
            self._json_response({"error": "dir and file params required"}, 400)
            return

        target = (PROJECT_DIR / output_dir / file_path).resolve()
        output_root = (PROJECT_DIR / output_dir).resolve()
        if not str(target).startswith(str(output_root)):
            self._json_response({"error": "Invalid path"}, 403)
            return

        if not target.exists():
            self._json_response({"error": "File not found"}, 404)
            return

        content = target.read_text(encoding="utf-8")
        self._json_response({
            "file": file_path,
            "content": content,
            "size": len(content),
            "lines": content.count("\n") + 1,
        })

    def _handle_verify(self, qs):
        """Verify a generated output directory — check all expected files exist and are valid."""
        output_dir = qs.get("dir", [""])[0]
        if not output_dir:
            self._json_response({"error": "dir param required"}, 400)
            return

        out = (PROJECT_DIR / output_dir).resolve()
        if not out.exists():
            self._json_response({"error": "Output directory not found"}, 404)
            return

        checks = []
        all_ok = True

        soul_files = list((out / "agent_workspaces").rglob("SOUL.md")) if (out / "agent_workspaces").exists() else []
        checks.append({
            "name": "SOUL.md 文件",
            "status": "ok" if soul_files else "fail",
            "detail": f"找到 {len(soul_files)} 个 Agent 的 SOUL.md",
            "items": [str(f.relative_to(out)) for f in sorted(soul_files)],
        })
        if not soul_files:
            all_ok = False

        has_routing = 0
        has_entry_tag = 0
        agent_details = []
        for sf in sorted(soul_files):
            content = sf.read_text(encoding="utf-8")
            agent_id = sf.parent.name
            routing_ok = "OpenClaw 协作规则" in content
            entry_ok = "🎯 入口 Agent" in content
            if routing_ok:
                has_routing += 1
            if entry_ok:
                has_entry_tag += 1
            agent_details.append({
                "id": agent_id,
                "lines": content.count("\n") + 1,
                "size": len(content),
                "has_routing": routing_ok,
                "is_entry": entry_ok,
            })

        checks.append({
            "name": "OpenClaw 路由规则",
            "status": "ok" if has_routing == len(soul_files) else "warn",
            "detail": f"{has_routing}/{len(soul_files)} 个 SOUL.md 包含 @agent_id 路由指令",
        })

        checks.append({
            "name": "入口 Agent 标记",
            "status": "ok" if has_entry_tag == 1 else ("warn" if has_entry_tag == 0 else "fail"),
            "detail": f"{has_entry_tag} 个 Agent 被标记为入口",
        })

        config_files = {
            "config/agents.yaml": "Agent 模型配置",
            "openclaw_agents.json": "OpenClaw 注册配置",
            "install_agents.sh": "安装脚本",
            "docs/permission_matrix.md": "权限矩阵文档",
            "docs/task_flow.md": "任务流转文档",
        }
        for fname, label in config_files.items():
            exists = (out / fname).exists()
            checks.append({
                "name": label,
                "status": "ok" if exists else "fail",
                "detail": f"{fname} {'✅ 存在' if exists else '❌ 缺失'}",
            })
            if not exists:
                all_ok = False

        self._json_response({
            "output_dir": str(out),
            "all_ok": all_ok,
            "checks": checks,
            "agents": agent_details,
        })

    def _safe_handle(self, handler, *args):
        """Wrap handler in try/except to always return JSON on errors."""
        try:
            handler(*args)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._json_response({"error": f"Internal error: {e}"}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/generate":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            self._safe_handle(self._handle_generate, body)
        else:
            self._json_response({"error": "Not found"}, 404)

    def _handle_generate(self, body):
        template_name = body.get("template", "")
        output_dir = body.get("output_dir", "./output")
        removed_agents = body.get("removed_agents", [])
        model_overrides = body.get("model_overrides", {})

        try:
            tpl = engine.load_template(template_name)
        except FileNotFoundError:
            self._json_response({"error": f"Template '{template_name}' not found"}, 404)
            return

        for agent_id in removed_agents:
            tpl = engine.remove_agent(tpl, agent_id)
        for agent_id, model in model_overrides.items():
            tpl = engine.set_model(tpl, agent_id, model)

        errors = tpl.validate()
        if errors:
            self._json_response({"error": "Validation failed", "details": errors}, 400)
            return

        out = (PROJECT_DIR / output_dir).resolve()
        out.mkdir(parents=True, exist_ok=True)
        renderer = TemplateRenderer(tpl, out)
        renderer.render_all()

        generated_files = []
        for agent in tpl.agents:
            soul = out / "agent_workspaces" / agent.id / "SOUL.md"
            if soul.exists():
                generated_files.append(f"agent_workspaces/{agent.id}/SOUL.md")
        for name in ["config/agents.yaml", "openclaw_agents.json",
                      "install_agents.sh", "docs/permission_matrix.md",
                      "docs/task_flow.md"]:
            if (out / name).exists():
                generated_files.append(name)

        entry = tpl.get_entry_agent()
        self._json_response({
            "status": "success",
            "template": tpl.name,
            "output_dir": str(out),
            "files": generated_files,
            "agent_count": len(tpl.agents),
            "entry_point": {
                "id": entry.id, "name": entry.name, "icon": entry.icon,
            } if entry else None,
            "next_steps": [
                f"查看 {out}/agent_workspaces/ 中的 SOUL.md 文件",
                f"编辑 {out}/config/agents.yaml 调整模型配置",
                f"运行 bash {out}/install_agents.sh 注册到 OpenClaw",
                f"在 OpenClaw 中向 {entry.icon} {entry.name} 发送消息开始使用" if entry else "",
            ],
        })

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path, content_type):
        if not path.exists():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        sys.stderr.write(f"  [{ts}] {fmt % args}\n")


def main():
    parser = argparse.ArgumentParser(description="三十六行 · The 36 Guilds — Web Server")
    parser.add_argument("--port", type=int, default=7892, help="Port (default 7892)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host (default 127.0.0.1)")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), GuildsHandler)
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  三十六行 · The 36 Guilds — Dashboard                    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print(f"  🌐 http://{args.host}:{args.port}")
    print(f"  📁 Templates: {len(engine.list_templates())} presets loaded")
    print()
    print("  Press Ctrl+C to stop")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  👋 Stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
