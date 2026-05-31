<div align="center">

# CodeRouter-CLI

**轻量级终端 AI 编程模型智能路由引擎**

[简体中文](#简体中文) | [繁體中文](#繁體中文) | [English](#english)

[![Version](https://img.shields.io/badge/version-v1.0.0-blue.svg)](https://github.com/gitstq/CodeRouter-CLI/releases)
[![Python](https://img.shields.io/badge/Python-3.8%2B-green.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-0-orange.svg)]()

一个纯 Python 实现的 AI 模型路由引擎，零外部依赖，开箱即用。支持多模型智能调度、自动故障转移、成本追踪与终端可视化管理。

</div>

---

## 简体中文

### 🎉 项目介绍

在日常 AI 编程开发中，我们常常需要同时对接多个大语言模型 API —— OpenAI、DeepSeek、通义千问、Claude……每个模型各有优劣，有的擅长代码生成，有的响应更快，有的价格更低。如何在一个统一的入口高效管理和调度这些模型？

**CodeRouter-CLI** 正是为了解决这个问题而生的。它是一个运行在终端中的轻量级 AI 模型智能路由引擎，能够：

- 将多个 AI 模型 API 统一代理为一个 **OpenAI 兼容接口**
- 根据预设策略**智能选择**最优模型
- 当某个模型不可用时**自动故障转移**到备用模型
- **实时追踪**每次调用的 Token 消耗和成本
- 通过终端 TUI 界面**可视化管理**所有模型

整个项目采用纯 Python 3.8+ 实现，**零外部依赖**，一条命令即可安装运行。

### ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 🧠 **智能路由引擎** | 内置 4 种路由策略 —— 优先级（priority）、轮询（round_robin）、最低延迟（least_latency）、随机（random），灵活应对不同场景 |
| 🔄 **自动故障转移** | 请求失败时自动重试并切换到下一个可用模型，连续失败自动标记为不健康，恢复后自动重新纳入调度 |
| 🌐 **OpenAI 兼容代理** | 对外暴露标准 `/v1/chat/completions` 接口，支持流式 SSE 和非流式两种响应模式，无缝对接各类 AI 编程工具 |
| 📊 **成本追踪引擎** | 实时记录每次请求的 Token 消耗与费用，支持按日/周/月汇总和按模型分类统计 |
| 🏥 **健康检测** | 后台定期探测各端点可用性，记录响应时间与成功率，自动标记与恢复不健康端点 |
| 🖥️ **TUI 交互界面** | 基于 curses 的终端可视化界面，直观查看和管理所有模型状态 |
| 📦 **零外部依赖** | 纯 Python 标准库实现，无需安装任何第三方包，`pip install -e .` 即可使用 |
| 🔧 **环境变量覆盖** | 支持通过环境变量覆盖配置项，方便在 Docker 等容器化环境中灵活部署 |

### 🚀 快速开始

#### 环境要求

- Python 3.8 或更高版本
- pip（Python 包管理器）
- 无需任何第三方依赖

#### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/gitstq/CodeRouter-CLI.git
cd CodeRouter-CLI

# 安装（开发模式）
pip install -e .
```

安装完成后，`coderouter` 命令即可在终端中使用。

#### 快速体验

```bash
# 1. 初始化默认配置
coderouter config init

# 2. 添加一个模型（以 OpenAI 为例）
coderouter config add \
  --name gpt-4o \
  --endpoint https://api.openai.com/v1/chat/completions \
  --api-key sk-your-api-key \
  --priority 1 \
  --cost-input 2.5 \
  --cost-output 10.0

# 3. 验证配置
coderouter config validate

# 4. 测试连通性
coderouter test

# 5. 启动 API 代理服务器
coderouter serve
```

服务器启动后，即可通过 `http://127.0.0.1:8199/v1/chat/completions` 统一访问 AI 模型。

### 📖 详细使用指南

#### CLI 命令一览

```bash
coderouter serve              # 启动 API 代理服务器
coderouter config show        # 查看当前完整配置
coderouter config list        # 列出所有已配置模型
coderouter config add         # 添加新模型
coderouter config remove      # 删除模型
coderouter config edit        # 编辑模型配置
coderouter config validate    # 验证配置是否正确
coderouter config init        # 重新初始化默认配置
coderouter stats              # 查看成本统计
coderouter stats --reset      # 重置统计数据
coderouter test               # 测试所有模型连通性
coderouter test --timeout 15  # 自定义超时时间（秒）
coderouter tui                # 启动 TUI 可视化界面
```

#### `coderouter serve` — 启动 API 代理服务器

这是最核心的命令，启动后对外提供 OpenAI 兼容的 API 代理服务。

```bash
# 使用默认配置启动
coderouter serve

# 指定监听地址和端口
coderouter serve --host 0.0.0.0 --port 9000

# 使用自定义配置文件
coderouter serve --config /path/to/custom-config.json
```

启动后可用的 API 端点：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/chat/completions` | POST | 聊天补全（支持流式/非流式） |
| `/v1/models` | GET | 获取已配置模型列表 |
| `/health` | GET | 查看所有端点健康状态 |
| `/stats` | GET | 获取成本统计数据 |

#### `coderouter config` — 模型配置管理

配置管理支持完整的 CRUD 操作。

**查看配置：**

```bash
# 显示完整配置（含敏感信息）
coderouter config show

# 列出所有模型（表格形式）
coderouter config list
```

**添加模型：**

```bash
coderouter config add \
  --name "deepseek-chat" \
  --endpoint "https://api.deepseek.com/v1/chat/completions" \
  --api-key "sk-your-key" \
  --priority 2 \
  --cost-input 0.14 \
  --cost-output 0.28 \
  --max-tokens 8192
```

**编辑模型：**

```bash
# 修改优先级和启用状态
coderouter config edit --name "gpt-4o" --priority 3 --enabled false

# 更新 API Key
coderouter config edit --name "gpt-4o" --api-key "sk-new-key"
```

**删除模型：**

```bash
coderouter config remove --name "deepseek-chat"
```

#### 配置文件详解

配置文件默认位于 `~/.coderouter/config.json`，首次运行时自动创建。完整格式如下：

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8199
  },
  "models": [
    {
      "name": "gpt-4o",
      "endpoint": "https://api.openai.com/v1/chat/completions",
      "api_key": "sk-xxx",
      "priority": 1,
      "cost_per_million_input": 2.5,
      "cost_per_million_output": 10.0,
      "max_tokens": 4096,
      "enabled": true
    }
  ],
  "routing": {
    "strategy": "priority",
    "timeout": 30,
    "max_retries": 3,
    "health_check_interval": 60
  },
  "tracker": {
    "enabled": true,
    "data_file": "~/.coderouter/stats.json"
  }
}
```

**配置字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `server.host` | string | 代理服务器监听地址 |
| `server.port` | integer | 代理服务器监听端口 |
| `models[].name` | string | 模型名称（用于路由选择和 API 请求） |
| `models[].endpoint` | string | 模型 API 端点 URL |
| `models[].api_key` | string | API 密钥 |
| `models[].priority` | integer | 优先级，数值越小优先级越高 |
| `models[].cost_per_million_input` | float | 每百万输入 Token 的价格（美元） |
| `models[].cost_per_million_output` | float | 每百万输出 Token 的价格（美元） |
| `models[].max_tokens` | integer | 最大 Token 数 |
| `models[].enabled` | boolean | 是否启用 |
| `routing.strategy` | string | 路由策略：`priority` / `round_robin` / `least_latency` / `random` |
| `routing.timeout` | integer | 请求超时时间（秒） |
| `routing.max_retries` | integer | 最大重试次数 |
| `routing.health_check_interval` | integer | 健康检测间隔（秒） |
| `tracker.enabled` | boolean | 是否启用成本追踪 |
| `tracker.data_file` | string | 统计数据存储路径 |

**环境变量覆盖：**

支持通过环境变量覆盖配置文件中的值，便于容器化部署：

```bash
export CODEROUTER_HOST=0.0.0.0
export CODEROUTER_PORT=9000
export CODEROUTER_STRATEGY=round_robin
export CODEROUTER_TIMEOUT=60
export CODEROUTER_MAX_RETRIES=5
export CODEROUTER_HEALTH_INTERVAL=30
export CODEROUTER_TRACKER_ENABLED=true
coderouter serve
```

#### 路由策略说明

| 策略 | 行为 | 适用场景 |
|------|------|----------|
| `priority` | 始终选择优先级最高（数值最小）的可用模型 | 有明确主备模型的场景 |
| `round_robin` | 按顺序轮流使用各可用模型 | 希望均匀分配负载的场景 |
| `least_latency` | 选择最近一次响应最快的模型 | 对响应速度敏感的场景 |
| `random` | 随机选择一个可用模型 | 无明显偏好的通用场景 |

#### `coderouter stats` — 成本统计

```bash
# 查看统计
coderouter stats

# 重置统计
coderouter stats --reset
```

输出包含：总请求数、总成本、Token 消耗明细、成功率、平均延迟、按模型分类统计、近 7 天每日统计。

#### `coderouter test` — 连通性测试

```bash
# 使用默认超时（10秒）测试所有已启用模型
coderouter test

# 自定义超时时间
coderouter test --timeout 20
```

#### `coderouter tui` — 终端可视化界面

```bash
coderouter tui
```

启动基于 curses 的终端交互界面，可以直观查看所有模型的状态、健康信息并进行管理操作。

#### 使用场景示例

**场景一：Cursor / Continue 等 AI 编程工具接入**

将 CodeRouter 作为中间代理层，让 AI 编程工具通过统一接口访问多个模型：

```bash
# 1. 配置多个模型
coderouter config add --name gpt-4o --endpoint https://api.openai.com/v1/chat/completions --api-key sk-xxx --priority 1
coderouter config add --name deepseek-chat --endpoint https://api.deepseek.com/v1/chat/completions --api-key sk-xxx --priority 2

# 2. 启动代理
coderouter serve

# 3. 在 AI 编程工具中将 API Base URL 设置为 http://127.0.0.1:8199/v1
```

**场景二：成本优化**

利用轮询策略均匀分配请求，降低单一模型的使用成本：

```json
{
  "routing": { "strategy": "round_robin" }
}
```

**场景三：高可用部署**

配置多个同类型模型作为互为备份，自动故障转移确保服务不中断。

### 💡 设计思路与迭代规划

#### 设计理念

CodeRouter-CLI 的核心设计原则是 **简单、可靠、零负担**：

- **纯标准库实现**：不引入任何第三方依赖，避免版本冲突和安全风险，安装即用
- **配置即代码**：所有行为通过 JSON 配置文件驱动，可版本管理、可复现
- **渐进式复杂度**：默认配置开箱即用，高级功能按需开启
- **OpenAI 兼容优先**：对外接口严格遵循 OpenAI API 格式，确保与现有生态无缝对接

#### 未来规划

- [ ] **v1.1** — 支持模型标签与分组，按请求内容智能匹配模型
- [ ] **v1.2** — Web Dashboard，提供浏览器端可视化管理界面
- [ ] **v1.3** — 速率限制与配额管理，防止单一模型过度消耗
- [ ] **v1.4** — 插件系统，支持自定义路由策略和中间件
- [ ] **v2.0** — 分布式部署支持，多节点协同调度

### 📦 部署指南

#### 本地开发部署

```bash
git clone https://github.com/gitstq/CodeRouter-CLI.git
cd CodeRouter-CLI
pip install -e .
coderouter config init
coderouter serve
```

#### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .

# 通过环境变量配置
ENV CODEROUTER_HOST=0.0.0.0
ENV CODEROUTER_PORT=8199

EXPOSE 8199

CMD ["coderouter", "serve"]
```

构建并运行：

```bash
docker build -t coderouter .
docker run -d \
  -p 8199:8199 \
  -e CODEROUTER_HOST=0.0.0.0 \
  -v ~/.coderouter:/root/.coderouter \
  coderouter
```

#### systemd 服务（Linux）

创建 `/etc/systemd/system/coderouter.service`：

```ini
[Unit]
Description=CodeRouter CLI API Proxy
After=network.target

[Service]
Type=simple
User=your-user
ExecStart=/usr/local/bin/coderouter serve
Restart=always
RestartSec=5
Environment=CODEROUTER_HOST=0.0.0.0

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable coderouter
sudo systemctl start coderouter
```

### 🤝 贡献指南

我们欢迎任何形式的贡献！无论是提交 Bug 报告、功能建议，还是直接提交 Pull Request。

#### 提交贡献

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m "feat: add your feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

#### 代码规范

- 遵循 PEP 8 编码规范
- 所有公共函数和类需包含中英双语 docstring
- 提交信息请使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式

#### 提交 Issue

- **Bug 报告**：请附上复现步骤、预期行为和实际行为
- **功能建议**：请描述使用场景和期望的行为

### 📄 开源协议

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 开源。

```
MIT License

Copyright (c) 2024 CodeRouter Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 繁體中文

### 🎉 專案介紹

在日常 AI 程式開發中，我們經常需要同時對接多個大型語言模型 API —— OpenAI、DeepSeek、通義千問、Claude……每個模型各有優劣，有的擅長程式碼生成，有的回應更快，有的價格更低。如何在一個統一的入口高效管理和調度這些模型？

**CodeRouter-CLI** 正是為了解決這個問題而誕生的。它是一個運行在終端中的輕量級 AI 模型智慧路由引擎，能夠：

- 將多個 AI 模型 API 統一代理為一個 **OpenAI 相容介面**
- 根據預設策略**智慧選擇**最優模型
- 當某個模型不可用時**自動故障轉移**到備用模型
- **即時追蹤**每次呼叫的 Token 消耗與成本
- 透過終端 TUI 介面**可視化管理**所有模型

整個專案採用純 Python 3.8+ 實現，**零外部依賴**，一條命令即可安裝運行。

### ✨ 核心特性

| 特性 | 說明 |
|------|------|
| 🧠 **智慧路由引擎** | 內建 4 種路由策略 —— 優先權（priority）、輪詢（round_robin）、最低延遲（least_latency）、隨機（random），靈活應對不同場景 |
| 🔄 **自動故障轉移** | 請求失敗時自動重試並切換到下一個可用模型，連續失敗自動標記為不健康，恢復後自動重新納入調度 |
| 🌐 **OpenAI 相容代理** | 對外暴露標準 `/v1/chat/completions` 介面，支援串流 SSE 和非串流兩種回應模式，無縫對接各類 AI 程式設計工具 |
| 📊 **成本追蹤引擎** | 即時記錄每次請求的 Token 消耗與費用，支援按日/週/月彙總和按模型分類統計 |
| 🏥 **健康檢測** | 後台定期探測各端點可用性，記錄回應時間與成功率，自動標記與恢復不健康端點 |
| 🖥️ **TUI 互動介面** | 基於 curses 的終端可視化介面，直觀查看和管理所有模型狀態 |
| 📦 **零外部依賴** | 純 Python 標準函式庫實現，無需安裝任何第三方套件，`pip install -e .` 即可使用 |
| 🔧 **環境變數覆蓋** | 支援透過環境變數覆蓋配置項，方便在 Docker 等容器化環境中靈活部署 |

### 🚀 快速開始

#### 環境要求

- Python 3.8 或更高版本
- pip（Python 套件管理器）
- 無需任何第三方依賴

#### 安裝步驟

```bash
# 克隆倉庫
git clone https://github.com/gitstq/CodeRouter-CLI.git
cd CodeRouter-CLI

# 安裝（開發模式）
pip install -e .
```

安裝完成後，`coderouter` 命令即可在終端中使用。

#### 快速體驗

```bash
# 1. 初始化預設配置
coderouter config init

# 2. 新增一個模型（以 OpenAI 為例）
coderouter config add \
  --name gpt-4o \
  --endpoint https://api.openai.com/v1/chat/completions \
  --api-key sk-your-api-key \
  --priority 1 \
  --cost-input 2.5 \
  --cost-output 10.0

# 3. 驗證配置
coderouter config validate

# 4. 測試連通性
coderouter test

# 5. 啟動 API 代理伺服器
coderouter serve
```

伺服器啟動後，即可透過 `http://127.0.0.1:8199/v1/chat/completions` 統一存取 AI 模型。

### 📖 詳細使用指南

#### CLI 命令一覽

```bash
coderouter serve              # 啟動 API 代理伺服器
coderouter config show        # 查看當前完整配置
coderouter config list        # 列出所有已配置模型
coderouter config add         # 新增新模型
coderouter config remove      # 刪除模型
coderouter config edit        # 編輯模型配置
coderouter config validate    # 驗證配置是否正確
coderouter config init        # 重新初始化預設配置
coderouter stats              # 查看成本統計
coderouter stats --reset      # 重置統計資料
coderouter test               # 測試所有模型連通性
coderouter test --timeout 15  # 自訂逾時時間（秒）
coderouter tui                # 啟動 TUI 可視化介面
```

#### `coderouter serve` — 啟動 API 代理伺服器

這是最核心的命令，啟動後對外提供 OpenAI 相容的 API 代理服務。

```bash
# 使用預設配置啟動
coderouter serve

# 指定監聽位址和連接埠
coderouter serve --host 0.0.0.0 --port 9000

# 使用自訂配置檔案
coderouter serve --config /path/to/custom-config.json
```

啟動後可用的 API 端點：

| 端點 | 方法 | 說明 |
|------|------|------|
| `/v1/chat/completions` | POST | 聊天補全（支援串流/非串流） |
| `/v1/models` | GET | 取得已配置模型列表 |
| `/health` | GET | 查看所有端點健康狀態 |
| `/stats` | GET | 取得成本統計資料 |

#### `coderouter config` — 模型配置管理

配置管理支援完整的 CRUD 操作。

**查看配置：**

```bash
# 顯示完整配置（含敏感資訊）
coderouter config show

# 列出所有模型（表格形式）
coderouter config list
```

**新增模型：**

```bash
coderouter config add \
  --name "deepseek-chat" \
  --endpoint "https://api.deepseek.com/v1/chat/completions" \
  --api-key "sk-your-key" \
  --priority 2 \
  --cost-input 0.14 \
  --cost-output 0.28 \
  --max-tokens 8192
```

**編輯模型：**

```bash
# 修改優先權和啟用狀態
coderouter config edit --name "gpt-4o" --priority 3 --enabled false

# 更新 API Key
coderouter config edit --name "gpt-4o" --api-key "sk-new-key"
```

**刪除模型：**

```bash
coderouter config remove --name "deepseek-chat"
```

#### 配置檔案詳解

配置檔案預設位於 `~/.coderouter/config.json`，首次運行時自動建立。完整格式如下：

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8199
  },
  "models": [
    {
      "name": "gpt-4o",
      "endpoint": "https://api.openai.com/v1/chat/completions",
      "api_key": "sk-xxx",
      "priority": 1,
      "cost_per_million_input": 2.5,
      "cost_per_million_output": 10.0,
      "max_tokens": 4096,
      "enabled": true
    }
  ],
  "routing": {
    "strategy": "priority",
    "timeout": 30,
    "max_retries": 3,
    "health_check_interval": 60
  },
  "tracker": {
    "enabled": true,
    "data_file": "~/.coderouter/stats.json"
  }
}
```

**配置欄位說明：**

| 欄位 | 類型 | 說明 |
|------|------|------|
| `server.host` | string | 代理伺服器監聽位址 |
| `server.port` | integer | 代理伺服器監聽連接埠 |
| `models[].name` | string | 模型名稱（用於路由選擇和 API 請求） |
| `models[].endpoint` | string | 模型 API 端點 URL |
| `models[].api_key` | string | API 金鑰 |
| `models[].priority` | integer | 優先權，數值越小優先權越高 |
| `models[].cost_per_million_input` | float | 每百萬輸入 Token 的價格（美元） |
| `models[].cost_per_million_output` | float | 每百萬輸出 Token 的價格（美元） |
| `models[].max_tokens` | integer | 最大 Token 數 |
| `models[].enabled` | boolean | 是否啟用 |
| `routing.strategy` | string | 路由策略：`priority` / `round_robin` / `least_latency` / `random` |
| `routing.timeout` | integer | 請求逾時時間（秒） |
| `routing.max_retries` | integer | 最大重試次數 |
| `routing.health_check_interval` | integer | 健康檢測間隔（秒） |
| `tracker.enabled` | boolean | 是否啟用成本追蹤 |
| `tracker.data_file` | string | 統計資料儲存路徑 |

**環境變數覆蓋：**

支援透過環境變數覆蓋配置檔案中的值，便於容器化部署：

```bash
export CODEROUTER_HOST=0.0.0.0
export CODEROUTER_PORT=9000
export CODEROUTER_STRATEGY=round_robin
export CODEROUTER_TIMEOUT=60
export CODEROUTER_MAX_RETRIES=5
export CODEROUTER_HEALTH_INTERVAL=30
export CODEROUTER_TRACKER_ENABLED=true
coderouter serve
```

#### 路由策略說明

| 策略 | 行為 | 適用場景 |
|------|------|----------|
| `priority` | 始終選擇優先權最高（數值最小）的可用模型 | 有明確主備模型的場景 |
| `round_robin` | 按順序輪流使用各可用模型 | 希望均勻分配負載的場景 |
| `least_latency` | 選擇最近一次回應最快的模型 | 對回應速度敏感的場景 |
| `random` | 隨機選擇一個可用模型 | 無明顯偏好的通用場景 |

#### `coderouter stats` — 成本統計

```bash
# 查看統計
coderouter stats

# 重置統計
coderouter stats --reset
```

輸出包含：總請求數、總成本、Token 消耗明細、成功率、平均延遲、按模型分類統計、近 7 天每日統計。

#### `coderouter test` — 連通性測試

```bash
# 使用預設逾時（10秒）測試所有已啟用模型
coderouter test

# 自訂逾時時間
coderouter test --timeout 20
```

#### `coderouter tui` — 終端可視化介面

```bash
coderouter tui
```

啟動基於 curses 的終端互動介面，可以直觀查看所有模型的狀態、健康資訊並進行管理操作。

#### 使用場景示例

**場景一：Cursor / Continue 等 AI 程式設計工具接入**

將 CodeRouter 作為中間代理層，讓 AI 程式設計工具透過統一介面存取多個模型：

```bash
# 1. 配置多個模型
coderouter config add --name gpt-4o --endpoint https://api.openai.com/v1/chat/completions --api-key sk-xxx --priority 1
coderouter config add --name deepseek-chat --endpoint https://api.deepseek.com/v1/chat/completions --api-key sk-xxx --priority 2

# 2. 啟動代理
coderouter serve

# 3. 在 AI 程式設計工具中將 API Base URL 設定為 http://127.0.0.1:8199/v1
```

**場景二：成本最佳化**

利用輪詢策略均勻分配請求，降低單一模型的使用成本：

```json
{
  "routing": { "strategy": "round_robin" }
}
```

**場景三：高可用部署**

配置多個同類型模型作為互為備份，自動故障轉移確保服務不中斷。

### 💡 設計思路與迭代規劃

#### 設計理念

CodeRouter-CLI 的核心設計原則是 **簡單、可靠、零負擔**：

- **純標準函式庫實現**：不引入任何第三方依賴，避免版本衝突和安全風險，安裝即用
- **配置即程式碼**：所有行為透過 JSON 配置檔案驅動，可版本管理、可重現
- **漸進式複雜度**：預設配置開箱即用，進階功能按需開啟
- **OpenAI 相容優先**：對外介面嚴格遵循 OpenAI API 格式，確保與現有生態系統無縫對接

#### 未來規劃

- [ ] **v1.1** — 支援模型標籤與分組，按請求內容智慧匹配模型
- [ ] **v1.2** — Web Dashboard，提供瀏覽器端可視化管理介面
- [ ] **v1.3** — 速率限制與配額管理，防止單一模型過度消耗
- [ ] **v1.4** — 外掛系統，支援自訂路由策略和中介軟體
- [ ] **v2.0** — 分散式部署支援，多節點協同調度

### 📦 部署指南

#### 本地開發部署

```bash
git clone https://github.com/gitstq/CodeRouter-CLI.git
cd CodeRouter-CLI
pip install -e .
coderouter config init
coderouter serve
```

#### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .

# 透過環境變數配置
ENV CODEROUTER_HOST=0.0.0.0
ENV CODEROUTER_PORT=8199

EXPOSE 8199

CMD ["coderouter", "serve"]
```

建置並運行：

```bash
docker build -t coderouter .
docker run -d \
  -p 8199:8199 \
  -e CODEROUTER_HOST=0.0.0.0 \
  -v ~/.coderouter:/root/.coderouter \
  coderouter
```

#### systemd 服務（Linux）

建立 `/etc/systemd/system/coderouter.service`：

```ini
[Unit]
Description=CodeRouter CLI API Proxy
After=network.target

[Service]
Type=simple
User=your-user
ExecStart=/usr/local/bin/coderouter serve
Restart=always
RestartSec=5
Environment=CODEROUTER_HOST=0.0.0.0

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable coderouter
sudo systemctl start coderouter
```

### 🤝 貢獻指南

我們歡迎任何形式的貢獻！無論是提交 Bug 回報、功能建議，還是直接提交 Pull Request。

#### 提交貢獻

1. Fork 本倉庫
2. 建立特性分支：`git checkout -b feature/your-feature`
3. 提交變更：`git commit -m "feat: add your feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

#### 程式碼規範

- 遵循 PEP 8 編碼規範
- 所有公共函式和類別需包含中英雙語 docstring
- 提交資訊請使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式

#### 提交 Issue

- **Bug 回報**：請附上重現步驟、預期行為和實際行為
- **功能建議**：請描述使用場景和期望的行為

### 📄 開源協議

本專案基於 [MIT License](https://opensource.org/licenses/MIT) 開源。

```
MIT License

Copyright (c) 2024 CodeRouter Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## English

### 🎉 Introduction

In day-to-day AI-assisted development, we often need to connect to multiple LLM APIs simultaneously — OpenAI, DeepSeek, Qwen, Claude... Each model has its own strengths: some excel at code generation, some respond faster, and some are more cost-effective. How can you efficiently manage and orchestrate all these models through a single unified entry point?

**CodeRouter-CLI** was built to solve exactly this problem. It is a lightweight AI model intelligent routing engine that runs right in your terminal, capable of:

- Proxying multiple AI model APIs behind a single **OpenAI-compatible interface**
- **Intelligently selecting** the optimal model based on configurable routing strategies
- **Automatically failing over** to backup models when one becomes unavailable
- **Tracking** token consumption and costs in real time for every request
- Providing a terminal TUI for **visual management** of all your models

The entire project is implemented in pure Python 3.8+ with **zero external dependencies** — install and run with a single command.

### ✨ Core Features

| Feature | Description |
|---------|-------------|
| 🧠 **Intelligent Routing Engine** | 4 built-in routing strategies — priority, round_robin, least_latency, random — to handle diverse use cases |
| 🔄 **Automatic Failover** | Automatically retries and switches to the next available model on failure; marks unhealthy endpoints and recovers them automatically |
| 🌐 **OpenAI-Compatible Proxy** | Exposes a standard `/v1/chat/completions` endpoint with both streaming SSE and non-streaming response modes for seamless integration with AI coding tools |
| 📊 **Cost Tracking Engine** | Records token consumption and costs per request in real time, with daily/weekly/monthly rollups and per-model breakdowns |
| 🏥 **Health Checking** | Periodically probes endpoint availability in the background, tracks response times and success rates, auto-marks and recovers unhealthy endpoints |
| 🖥️ **TUI Interface** | A curses-based terminal UI for visually inspecting and managing all model states |
| 📦 **Zero External Dependencies** | Built entirely with the Python standard library — no third-party packages needed, just `pip install -e .` |
| 🔧 **Environment Variable Overrides** | Override any config value via environment variables for flexible containerized deployments |

### 🚀 Quick Start

#### Prerequisites

- Python 3.8 or later
- pip (Python package manager)
- No third-party dependencies required

#### Installation

```bash
# Clone the repository
git clone https://github.com/gitstq/CodeRouter-CLI.git
cd CodeRouter-CLI

# Install in development mode
pip install -e .
```

Once installed, the `coderouter` command is available in your terminal.

#### Quick Tryout

```bash
# 1. Initialize default configuration
coderouter config init

# 2. Add a model (e.g., OpenAI)
coderouter config add \
  --name gpt-4o \
  --endpoint https://api.openai.com/v1/chat/completions \
  --api-key sk-your-api-key \
  --priority 1 \
  --cost-input 2.5 \
  --cost-output 10.0

# 3. Validate configuration
coderouter config validate

# 4. Test connectivity
coderouter test

# 5. Start the API proxy server
coderouter serve
```

Once the server is running, you can access your AI models through the unified endpoint at `http://127.0.0.1:8199/v1/chat/completions`.

### 📖 Detailed Usage Guide

#### CLI Commands Overview

```bash
coderouter serve              # Start the API proxy server
coderouter config show        # Show current full configuration
coderouter config list        # List all configured models
coderouter config add         # Add a new model
coderouter config remove      # Remove a model
coderouter config edit        # Edit model configuration
coderouter config validate    # Validate configuration
coderouter config init        # Re-initialize default configuration
coderouter stats              # View cost statistics
coderouter stats --reset      # Reset statistics
coderouter test               # Test connectivity for all models
coderouter test --timeout 15  # Custom timeout in seconds
coderouter tui                # Launch the TUI interface
```

#### `coderouter serve` — Start the API Proxy Server

This is the core command. Once started, it provides an OpenAI-compatible API proxy service.

```bash
# Start with default configuration
coderouter serve

# Specify host and port
coderouter serve --host 0.0.0.0 --port 9000

# Use a custom config file
coderouter serve --config /path/to/custom-config.json
```

Available API endpoints after startup:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | Chat completions (streaming and non-streaming) |
| `/v1/models` | GET | List configured models |
| `/health` | GET | Health status of all endpoints |
| `/stats` | GET | Cost tracking statistics |

#### `coderouter config` — Model Configuration Management

Full CRUD operations for model configuration.

**Viewing configuration:**

```bash
# Show full configuration (includes sensitive data)
coderouter config show

# List all models in tabular format
coderouter config list
```

**Adding a model:**

```bash
coderouter config add \
  --name "deepseek-chat" \
  --endpoint "https://api.deepseek.com/v1/chat/completions" \
  --api-key "sk-your-key" \
  --priority 2 \
  --cost-input 0.14 \
  --cost-output 0.28 \
  --max-tokens 8192
```

**Editing a model:**

```bash
# Change priority and enabled status
coderouter config edit --name "gpt-4o" --priority 3 --enabled false

# Update API key
coderouter config edit --name "gpt-4o" --api-key "sk-new-key"
```

**Removing a model:**

```bash
coderouter config remove --name "deepseek-chat"
```

#### Configuration File Reference

The configuration file is located at `~/.coderouter/config.json` by default and is created automatically on first run. The full format is as follows:

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8199
  },
  "models": [
    {
      "name": "gpt-4o",
      "endpoint": "https://api.openai.com/v1/chat/completions",
      "api_key": "sk-xxx",
      "priority": 1,
      "cost_per_million_input": 2.5,
      "cost_per_million_output": 10.0,
      "max_tokens": 4096,
      "enabled": true
    }
  ],
  "routing": {
    "strategy": "priority",
    "timeout": 30,
    "max_retries": 3,
    "health_check_interval": 60
  },
  "tracker": {
    "enabled": true,
    "data_file": "~/.coderouter/stats.json"
  }
}
```

**Field Reference:**

| Field | Type | Description |
|-------|------|-------------|
| `server.host` | string | Proxy server listen address |
| `server.port` | integer | Proxy server listen port |
| `models[].name` | string | Model name (used for routing and API requests) |
| `models[].endpoint` | string | Model API endpoint URL |
| `models[].api_key` | string | API key |
| `models[].priority` | integer | Priority — lower values indicate higher priority |
| `models[].cost_per_million_input` | float | Cost per million input tokens (USD) |
| `models[].cost_per_million_output` | float | Cost per million output tokens (USD) |
| `models[].max_tokens` | integer | Maximum token count |
| `models[].enabled` | boolean | Whether the model is enabled |
| `routing.strategy` | string | Routing strategy: `priority` / `round_robin` / `least_latency` / `random` |
| `routing.timeout` | integer | Request timeout in seconds |
| `routing.max_retries` | integer | Maximum retry attempts |
| `routing.health_check_interval` | integer | Health check interval in seconds |
| `tracker.enabled` | boolean | Whether cost tracking is enabled |
| `tracker.data_file` | string | Path for statistics data storage |

**Environment Variable Overrides:**

Override any configuration value via environment variables for containerized deployments:

```bash
export CODEROUTER_HOST=0.0.0.0
export CODEROUTER_PORT=9000
export CODEROUTER_STRATEGY=round_robin
export CODEROUTER_TIMEOUT=60
export CODEROUTER_MAX_RETRIES=5
export CODEROUTER_HEALTH_INTERVAL=30
export CODEROUTER_TRACKER_ENABLED=true
coderouter serve
```

#### Routing Strategies

| Strategy | Behavior | Best For |
|----------|----------|----------|
| `priority` | Always selects the available model with the highest priority (lowest numeric value) | Scenarios with clear primary/backup models |
| `round_robin` | Cycles through available models in order | Evenly distributing load across models |
| `least_latency` | Selects the model with the fastest last response time | Latency-sensitive workloads |
| `random` | Randomly selects an available model | General-purpose use with no strong preference |

#### `coderouter stats` — Cost Statistics

```bash
# View statistics
coderouter stats

# Reset statistics
coderouter stats --reset
```

Output includes: total requests, total cost, token consumption breakdown, success rate, average latency, per-model statistics, and daily stats for the last 7 days.

#### `coderouter test` — Connectivity Test

```bash
# Test all enabled models with default timeout (10s)
coderouter test

# Custom timeout
coderouter test --timeout 20
```

#### `coderouter tui` — Terminal UI

```bash
coderouter tui
```

Launches a curses-based interactive terminal interface where you can visually inspect model statuses, health information, and perform management operations.

#### Use Case Examples

**Use Case 1: Connecting AI Coding Tools (Cursor / Continue, etc.)**

Use CodeRouter as a middleware proxy layer to let your AI coding tools access multiple models through a unified interface:

```bash
# 1. Configure multiple models
coderouter config add --name gpt-4o --endpoint https://api.openai.com/v1/chat/completions --api-key sk-xxx --priority 1
coderouter config add --name deepseek-chat --endpoint https://api.deepseek.com/v1/chat/completions --api-key sk-xxx --priority 2

# 2. Start the proxy
coderouter serve

# 3. Set the API Base URL in your AI coding tool to http://127.0.0.1:8199/v1
```

**Use Case 2: Cost Optimization**

Use the round-robin strategy to distribute requests evenly and reduce costs on any single model:

```json
{
  "routing": { "strategy": "round_robin" }
}
```

**Use Case 3: High Availability**

Configure multiple models of the same type as mutual backups with automatic failover to ensure uninterrupted service.

### 💡 Design Philosophy & Roadmap

#### Design Principles

The core design philosophy of CodeRouter-CLI is **simple, reliable, zero-burden**:

- **Pure standard library** — No third-party dependencies, eliminating version conflicts and security risks; install and run immediately
- **Configuration as code** — All behavior is driven by a JSON config file that can be version-controlled and reproduced
- **Progressive complexity** — Sensible defaults out of the box; advanced features enabled on demand
- **OpenAI compatibility first** — External interfaces strictly follow the OpenAI API format for seamless integration with the existing ecosystem

#### Roadmap

- [ ] **v1.1** — Model tags and groups for intelligent model matching based on request content
- [ ] **v1.2** — Web Dashboard for browser-based visual management
- [ ] **v1.3** — Rate limiting and quota management to prevent overconsumption on individual models
- [ ] **v1.4** — Plugin system for custom routing strategies and middleware
- [ ] **v2.0** — Distributed deployment support with multi-node coordinated scheduling

### 📦 Deployment Guide

#### Local Development

```bash
git clone https://github.com/gitstq/CodeRouter-CLI.git
cd CodeRouter-CLI
pip install -e .
coderouter config init
coderouter serve
```

#### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .

# Configure via environment variables
ENV CODEROUTER_HOST=0.0.0.0
ENV CODEROUTER_PORT=8199

EXPOSE 8199

CMD ["coderouter", "serve"]
```

Build and run:

```bash
docker build -t coderouter .
docker run -d \
  -p 8199:8199 \
  -e CODEROUTER_HOST=0.0.0.0 \
  -v ~/.coderouter:/root/.coderouter \
  coderouter
```

#### systemd Service (Linux)

Create `/etc/systemd/system/coderouter.service`:

```ini
[Unit]
Description=CodeRouter CLI API Proxy
After=network.target

[Service]
Type=simple
User=your-user
ExecStart=/usr/local/bin/coderouter serve
Restart=always
RestartSec=5
Environment=CODEROUTER_HOST=0.0.0.0

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable coderouter
sudo systemctl start coderouter
```

### 🤝 Contributing

We welcome contributions of all kinds! Whether it's a bug report, a feature suggestion, or a direct pull request.

#### How to Contribute

1. Fork this repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push the branch: `git push origin feature/your-feature`
5. Submit a Pull Request

#### Code Standards

- Follow PEP 8 coding conventions
- All public functions and classes must include bilingual (Chinese/English) docstrings
- Use [Conventional Commits](https://www.conventionalcommits.org/) format for commit messages

#### Filing Issues

- **Bug reports**: Please include reproduction steps, expected behavior, and actual behavior
- **Feature requests**: Please describe the use case and expected behavior

### 📄 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

```
MIT License

Copyright (c) 2024 CodeRouter Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
