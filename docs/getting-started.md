# 🚀 Getting Started — 从 Telegram / Lark 使用多 Agent 协作

本指南帮助你在 OpenClaw 上设置三十六行多 Agent 系统，并通过 Telegram 或 Lark（飞书）使用。

---

## 整体架构

```
你（用户）
  │
  │  Telegram / Lark / Signal
  ▼
┌─────────────────────────────┐
│   OpenClaw Gateway          │  ← 运行在你的 VPS / 本机
│   (消息路由 + Agent 管理)    │
└──────┬──────────────────────┘
       │
       ▼
┌──────────────┐
│ 🎯 入口 Agent │  ← 用户的所有消息都发给 TA（如 CTO / 太子）
│  (SOUL.md)    │
└──────┬───────┘
       │ @agent_id 内部消息
       ▼
┌──────────────────────────────────────┐
│   其他 Agent（PM、TechLead、QA...）    │
│   通过 @mentions 互相协作              │
│   每个 Agent 有自己的 SOUL.md          │
└──────────────────────────────────────┘
```

**关键概念：**
- 用户只和 **入口 Agent** 对话（通过 TG/Lark）
- 入口 Agent 自动把任务拆分、转发给其他 Agent（通过 OpenClaw 内部消息）
- 其他 Agent 之间通过 `@agent_id` 互相通讯
- 最终结果由入口 Agent 汇总后回复给用户

---

## Step 1：前置条件

确保你已经有：

- [ ] 一台 VPS 或本地机器（Linux / macOS）
- [ ] Python 3.9+
- [ ] OpenClaw 已安装并运行（[OpenClaw 官网](https://openclaw.ai)）
- [ ] 至少一个消息渠道已配置好：
  - **Telegram**：已创建 Bot（通过 [@BotFather](https://t.me/BotFather)），拿到 Bot Token
  - **Lark/飞书**：已创建应用，拿到 App ID 和 App Secret

---

## Step 2：安装三十六行

```bash
# SSH 到你的 VPS（或在本机操作）
git clone https://github.com/BruceLanLan/the-36-guilds.git
cd the-36-guilds
pip install pyyaml
```

---

## Step 3：选择模版并生成

### 方式 A：Web UI（推荐）

```bash
python3 server.py
# 如果在 VPS 上，用 SSH 隧道：
# ssh -L 7892:localhost:7892 user@your-vps
# 然后打开 http://localhost:7892
```

在 Web UI 中：
1. 点击想要的模版卡片
2. 查看流水线、Agent 列表、权限矩阵
3. 点击「⚡ 一键生成 Agent 团队」

### 方式 B：命令行

```bash
# 查看所有模版
python3 setup_guilds.py --list

# 选择模版并生成（推荐生成到 OpenClaw 目录旁边）
python3 setup_guilds.py --template it_company --output ~/openclaw-agents
```

### 模版选择指南

| 你的场景 | 推荐模版 | 命令 |
|---------|---------|------|
| 通用软件开发 | 🏢 现代IT公司 | `--template it_company` |
| 投资研究/交易 | 💰 投资机构 | `--template investment_firm` |
| 量化策略开发 | 📊 量化交易团队 | `--template quant_trading` |
| 需要严格审核 | 🏛️ 古代宫廷制 | `--template imperial_court` |

---

## Step 4：注册 Agent 到 OpenClaw

### 自动注册（推荐）

```bash
# 运行安装脚本
bash ~/openclaw-agents/install_agents.sh
```

安装脚本会自动：
- ✅ 创建各 Agent 的工作区目录
- ✅ SOUL.md 文件已就位
- ✅ 用 `openclaw agent create` 注册所有 Agent
- ✅ 设置 Agent 间的通讯权限
- ✅ 重启 OpenClaw Gateway

### 手动注册

如果自动脚本遇到问题，可以手动操作：

```bash
# 1. 将生成的 agent_workspaces 目录复制到 OpenClaw 的位置
cp -r ~/openclaw-agents/agent_workspaces/* ~/.openclaw/workspaces/

# 2. 参考 openclaw_agents.json 手动注册
cat ~/openclaw-agents/openclaw_agents.json

# 3. 逐个注册 Agent（以 IT 公司模版为例）
openclaw agent create --id cto --name "👔 CTO" --workspace ~/.openclaw/workspaces/cto
openclaw agent create --id product_manager --name "📋 产品经理" --workspace ~/.openclaw/workspaces/product_manager
# ... 其余 Agent 类似

# 4. 重启 Gateway
openclaw gateway restart
```

---

## Step 5：连接 Telegram / Lark 到入口 Agent

### Telegram 设置

1. **确认你的 Bot Token 已配置在 OpenClaw 中**

   OpenClaw 的配置文件（通常是 `openclaw.json` 或环境变量）中应该有：
   ```json
   {
     "telegram": {
       "bot_token": "你的BOT_TOKEN",
       "enabled": true
     }
   }
   ```

2. **将 Telegram Bot 绑定到入口 Agent**

   确保 OpenClaw 的 Telegram 渠道路由到入口 Agent：

   | 模版 | 入口 Agent ID | 绑定命令 |
   |------|-------------|---------|
   | 🏢 IT公司 | `cto` | `openclaw channel set telegram --agent cto` |
   | 💰 投资机构 | `cio` | `openclaw channel set telegram --agent cio` |
   | 📊 量化团队 | `chief_strategist` | `openclaw channel set telegram --agent chief_strategist` |
   | 🏛️ 宫廷制 | `taizi` | `openclaw channel set telegram --agent taizi` |

3. **重启 Gateway**
   ```bash
   openclaw gateway restart
   ```

4. **测试**

   在 Telegram 中给你的 Bot 发一条消息：
   ```
   帮我设计一个用户注册系统，要求 RESTful API + PostgreSQL + JWT 鉴权
   ```

   如果一切正常，Bot（CTO Agent）会回复，并在内部开始任务流转。

### Lark / 飞书 设置

1. **在飞书开放平台创建应用**
   - 前往 [open.feishu.cn](https://open.feishu.cn)
   - 创建企业自建应用
   - 获取 App ID 和 App Secret
   - 开启「机器人」能力

2. **在 OpenClaw 中配置飞书**
   ```json
   {
     "lark": {
       "app_id": "你的APP_ID",
       "app_secret": "你的APP_SECRET",
       "enabled": true
     }
   }
   ```

3. **绑定到入口 Agent**
   ```bash
   openclaw channel set lark --agent cto
   ```

4. **测试**

   在飞书中给机器人发消息即可。

---

## Step 6：开始使用

### 使用方式

你只需要在 TG / Lark 中给 Bot 发消息。**不需要知道内部有多少个 Agent**。

**简单任务**（入口 Agent 直接回答）：
```
Python 的 list 和 tuple 有什么区别？
```

**复杂任务**（自动触发多 Agent 协作）：
```
帮我设计一个用户注册系统，要求：
1. RESTful API（FastAPI）
2. PostgreSQL 数据库
3. JWT 鉴权
4. 完整测试用例
```

**IT 公司模版内部流转过程**（用户不可见）：
```
你的消息 → 👔 CTO（接收评估）
  → 📋 PM（拆解需求、写 PRD）
  → 🏗️ TechLead（技术评审 — 可打回 PM 修改）
  → 📊 ProjMgr（分配任务）
  → [🎨前端 + ⚙️后端 + 🔧DevOps]（并行开发）
  → 🧪 QA（测试验收 — 可打回修复）
  → 👔 CTO（汇总结果）→ 回复给你
```

### 查看 Agent 状态

```bash
# 查看所有 Agent 状态
openclaw agent list

# 查看特定 Agent 的会话
openclaw agent sessions --id cto
```

---

## 常见问题

### Q: Agent 之间的消息我能看到吗？

默认不能。Agent 间通过 OpenClaw 内部消息通讯，你只看到入口 Agent 的最终回复。
如果需要查看内部流转，可以查看 OpenClaw 的日志或使用 edict 风格的看板。

### Q: 我可以同时跟多个 Agent 对话吗？

可以！如果你注册了多个 Telegram Bot，每个绑定到不同的 Agent，就可以直接和他们对话。
但推荐的方式是只通过入口 Agent，让系统自动路由。

### Q: 审核关卡是怎么工作的？

以 IT 公司模版为例：
- TechLead 收到方案后会审查，不合格会打回给 PM 修改
- QA 测试不通过会打回给 ProjMgr 安排修复
- 这些都在 SOUL.md 中定义，Agent 会自动遵循

### Q: 我可以修改某个 Agent 的行为吗？

可以。编辑对应 Agent 的 `SOUL.md` 文件，然后重启 Gateway：
```bash
vim ~/openclaw-agents/agent_workspaces/cto/SOUL.md
openclaw gateway restart
```

### Q: 可以换模型吗？

可以。编辑 `config/agents.yaml`，为每个 Agent 指定不同的 LLM：
```yaml
agents:
  cto:
    model: gpt-4o
  product_manager:
    model: claude-3-sonnet
  frontend_dev:
    model: deepseek-coder
```

---

## 完整操作速查

```bash
# 1. 安装
git clone https://github.com/BruceLanLan/the-36-guilds.git
cd the-36-guilds && pip install pyyaml

# 2. 生成（选一种）
python3 server.py                                              # Web UI
python3 setup_guilds.py --template it_company --output ~/oc    # CLI

# 3. 注册到 OpenClaw
bash ~/oc/install_agents.sh

# 4. 绑定 TG/Lark 到入口 Agent
openclaw channel set telegram --agent cto

# 5. 重启
openclaw gateway restart

# 6. 在 TG 给 Bot 发消息，开始使用！
```
