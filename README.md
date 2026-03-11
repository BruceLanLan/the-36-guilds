# 三十六行 · The 36 Guilds

**行行出状元 — Every guild has its champion.**

> 别再让一个 Agent 当超人了。给你的 AI 团队定岗定编，像真正的组织一样协作。

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🤔 为什么需要这个？

大多数人用 AI Agent 的方式是这样的：

> _"来，一个 Agent，帮我搞定所有事情。"_

结果就是：上下文爆炸、输出质量不稳定、没法并行、出错了不知道是哪个环节。

**三十六行的思路** —— 像人类组织一样分工协作：

```
一个超人 Agent ❌  →  一个专业团队 ✅

用户 → CEO(接收) → PM(规划) → TechLead(审核) → 开发团队(并行执行) → QA(验收) → 交付
```

| 痛点 | 单 Agent | 三十六行 |
|------|---------|---------|
| 上下文超长 | ❌ 所有信息塞一个窗口 | ✅ 每个 Agent 只关注自己的职责 |
| 产出质量 | ⚠️ 没有审核机制 | ✅ 审核关卡可封驳打回 |
| 并行效率 | ❌ 串行处理 | ✅ 多 Agent 并行执行 |
| 出错定位 | ❌ 一坨结果不知道哪错了 | ✅ 每个环节可追踪 |
| 专业深度 | ⚠️ 通才=啥都不精 | ✅ 专职 Agent 专项能力 |

## ✨ 核心特性

- 🏢 **4 套预置组织架构模版**（IT 公司 / 投资机构 / 量化团队 / 古代宫廷制）
- 📝 **YAML 定义一切** — 一个 YAML 文件就是一个组织
- 🔍 **审核关卡** — 关键节点有独立审核人，可打回不合格产出
- 🔒 **权限矩阵** — Agent 间通讯有严格权限，不能越级
- ⚡ **一键生成** — SOUL.md + config + install script + 文档全部自动生成
- ✏️ **完全可定制** — 选择模版 → 修改 → 导出 → 使用自己的组织架构
- 🔌 **OpenClaw 集成** — 自动生成 OpenClaw 注册配置和安装脚本
- 🌐 **Web UI 看板** — 可视化选择模版、查看流水线、一键生成

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/BruceLanLan/the-36-guilds.git
cd the-36-guilds
pip install pyyaml
```

### 方式 1：Web UI（推荐）

```bash
python3 server.py
# 打开浏览器 → http://127.0.0.1:7892
```

Web UI 提供：
- 模版画廊 — 浏览所有组织架构模版
- 流水线可视化 — 查看任务流转和审核关卡
- Agent 详情 — 每个 Agent 的角色、职责、权限
- 权限矩阵 — 可视化 Agent 间通讯权限
- 一键生成 — 点击按钮即可生成所有文件

### 方式 2：命令行

```bash
# 列出所有可用模版
python3 setup_guilds.py --list

# 选择「现代IT公司」模版，一键生成
python3 setup_guilds.py --template it_company --output ./my_team

# 查看生成的文件
tree ./my_team
```

输出：

```
my_team/
├── agent_workspaces/
│   ├── cto/SOUL.md              # 👔 CTO — 任务接收
│   ├── product_manager/SOUL.md  # 📋 产品经理 — 需求分析
│   ├── tech_lead/SOUL.md        # 🏗️ 技术负责人 — 技术评审
│   ├── project_manager/SOUL.md  # 📊 项目经理 — 任务分配
│   ├── frontend_dev/SOUL.md     # 🎨 前端工程师
│   ├── backend_dev/SOUL.md      # ⚙️ 后端工程师
│   ├── devops/SOUL.md           # 🔧 DevOps
│   └── qa_engineer/SOUL.md      # 🧪 QA — 质量验收
├── config/agents.yaml
├── openclaw_agents.json
├── install_agents.sh
└── docs/
    ├── permission_matrix.md
    └── task_flow.md
```

### 在 OpenClaw 中使用（Telegram / Lark / Signal）

> **📖 完整的 TG/Lark 设置指南**：[docs/getting-started.md](docs/getting-started.md)

快速流程：

```bash
# 1. 生成 Agent 团队
python3 setup_guilds.py --template it_company --output ~/openclaw-agents

# 2. 注册到 OpenClaw
bash ~/openclaw-agents/install_agents.sh

# 3. 绑定 TG/Lark 到入口 Agent
openclaw channel set telegram --agent cto

# 4. 重启 Gateway
openclaw gateway restart

# 5. 在 TG/Lark 给 Bot 发消息，开始使用！
```

| 模版 | 入口 Agent | 你只需要和 TA 对话 |
|------|-----------|------------------|
| 🏢 IT公司 | 👔 CTO (`cto`) | 所有技术需求 |
| 💰 投资机构 | 🎯 首席投资官 (`cio`) | 投资研究任务 |
| 📊 量化团队 | 🧠 首席策略师 (`chief_strategist`) | 量化策略开发 |
| 🏛️ 宫廷制 | 👑 太子 (`taizi`) | 任何任务 |

> **核心概念**：用户只需要和「入口 Agent」对话（通过 TG/Lark）。
> TA 会自动把任务拆分、转发给其他 Agent（通过 `@agent_id`）。
> 审核关卡的 Agent 有权打回不合格产出。整个过程对用户透明。

### 交互式模式

```bash
python3 setup_guilds.py
```

支持：选择模版 → 预览 → 自定义（删除 Agent、换模型）→ 生成

## 📋 预置模版

### 🏢 现代 IT 公司 (默认推荐)

**适合**：软件开发、产品迭代、技术项目

```
👔CTO → 📋PM(规划) → 🏗️TechLead(评审✋) → 📊ProjMgr(分配)
  → [🎨前端 + ⚙️后端 + 🔧DevOps] → 🧪QA(验收✋) → 交付
```

8 个 Agent · 6 个阶段 · Tech Lead + QA 双重审核

---

### 💰 投资机构

**适合**：投研分析、交易策略、资产配置

```
🎯CIO → 🔬研究总监 → [📐量化 + 📊基本面] → 🛡️风控(审查✋)
  → 💼组合经理 → 📈交易员 → 📑运营报告
```

8 个 Agent · 6 个阶段 · 独立风控审查

---

### 📊 量化交易团队

**适合**：量化策略开发、自动化交易

```
🧠策略师 → [🔬研究员 + 🗄️数据工程师] → 🛡️风控官(审查✋)
  → ⚡执行交易员 → [🖥️系统工程师 + 📉绩效分析师]
```

7 个 Agent · 5 个阶段 · 从策略研发到执行全链路

---

### 🏛️ 古代宫廷制

**适合**：需要严格审核流程的复杂项目

```
👑太子(分拣) → 📜中书省(规划) → 🔍门下省(审核/封驳✋)
  → 📮尚书省(派发) → [💰户 + 📝礼 + ⚔️兵 + ⚖️刑 + 🔧工] → 回奏
```

11 个 Agent · 6 个阶段 · 门下省强制审核机制

> 灵感来源：[cft0808/edict](https://github.com/cft0808/edict) — 三省六部制

## 🔧 自定义模版

### 方法 1：基于现有模版修改

```bash
cp guilds/presets/it_company.yaml guilds/presets/my_team.yaml
# 编辑 my_team.yaml：增删 Agent、调整权限、修改流程
python3 setup_guilds.py --custom guilds/presets/my_team.yaml
```

### 方法 2：从零创建

创建一个 YAML 文件，包含以下结构：

```yaml
template:
  name: "我的团队"
  name_en: "My Team"
  icon: "🚀"
  version: "1.0"
  category: "custom"

stages:
  - id: intake
    name: "接收"
    description: "任务接收"
  - id: execution
    name: "执行"
    description: "任务执行"

agents:
  - id: leader
    name: "队长"
    icon: "👑"
    role: "Team Lead"
    stage: intake
    description: "接收任务，分配工作"
    responsibilities:
      - "接收外部任务"
      - "分配给团队成员"
    soul: |
      你是团队队长，负责接收任务并分配给合适的成员。

  - id: worker_a
    name: "执行者A"
    icon: "⚡"
    role: "Worker A"
    stage: execution
    description: "执行具体任务"
    responsibilities:
      - "完成分配的任务"
    soul: |
      你是执行者A，专注于完成队长分配的任务。

permissions:
  leader: [worker_a]
  worker_a: [leader]

task_flow:
  - from: leader
    to: worker_a
    action: "分配任务"
  - from: worker_a
    to: leader
    action: "提交结果"

review_gates: []
```

### 方法 3：Python API

```python
from guilds import TemplateEngine, TemplateRenderer, AgentDef
from pathlib import Path

engine = TemplateEngine()

# 加载模版
template = engine.load_template("it_company")

# 自定义：删除 Agent
template = engine.remove_agent(template, "devops")

# 自定义：改模型
template = engine.set_model(template, "cto", "gpt-4o")

# 导出为新模版
engine.export_yaml(template, Path("my_custom.yaml"))

# 生成所有文件
renderer = TemplateRenderer(template, Path("./output"))
renderer.render_all()
```

## 📁 项目结构

```
the-36-guilds/
├── guilds/                     # Python 包
│   ├── __init__.py
│   ├── schema.py               # 数据模型（Agent、Stage、权限等）
│   ├── engine.py               # 模版引擎（加载、验证、自定义、导出）
│   ├── renderer.py             # 渲染器（生成 SOUL.md、config、脚本）
│   └── presets/                # 预置模版
│       ├── imperial_court.yaml # 🏛️ 古代宫廷制（11 agents）
│       ├── it_company.yaml     # 🏢 现代IT公司（8 agents）
│       ├── investment_firm.yaml# 💰 投资机构（8 agents）
│       └── quant_trading.yaml  # 📊 量化交易团队（7 agents）
├── setup_guilds.py             # CLI 入口
├── tests/
│   └── test_engine.py
├── examples/
│   └── it_company_output/      # IT公司模版的生成示例
└── README.md
```

## 🗺️ Roadmap

- [x] **Phase 1** — 模版系统核心（4 个预置 · CLI · 自定义 · 渲染）
- [ ] **Phase 2** — Web UI 看板（实时任务流转可视化）
- [ ] **Phase 3** — 更多模版（军事指挥部 · 医疗团队 · 内容编辑部 · 客服分级响应）
- [ ] **Phase 4** — 模版市场（社区分享和发现）
- [ ] **Phase 5** — 运行时引擎（按 task_flow 自动路由消息）

## 🤝 贡献

欢迎贡献新的组织架构模版！只需要：

1. 在 `guilds/presets/` 创建一个 YAML 文件
2. 定义 agents、permissions、task_flow、review_gates
3. 提交 PR

特别欢迎：
- 🌍 不同文化/历史的组织架构（罗马军团、日本幕府、维京舰队...）
- 🏢 不同行业的团队架构（医疗、法律、教育...）
- 🎮 游戏/奇幻风格的架构（RPG 冒险队、太空舰队...）

## 📄 License

MIT

---

**三十六行，行行出状元。**
**Among the 36 guilds, every guild has its champion.**

让每个 Agent 都成为自己领域的状元 ⚔️
