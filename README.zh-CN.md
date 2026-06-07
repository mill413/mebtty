# WebTTY

<p align="center">
  <strong>自托管的企业级 Web 终端平台</strong><br>
  通过现代浏览器从任何地方访问服务器 —— 无需 SSH 客户端。
</p>

<p align="center">
  <a href="README.md">English</a> | <strong>简体中文</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/vue-3.4%2B-brightgreen?logo=vue.js&logoColor=white" alt="Vue">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
</p>

---

## 功能特性

- **完整的终端体验** — 支持 bash、zsh、fish 等任意 shell，完整的 PTY 支持
- **交互式程序** — vim、less、top、htop 等 TUI 应用完美运行
- **多标签页界面** — 在单个浏览器窗口中打开多个终端会话
- **设置页标签化** — 设置页面作为标签页打开，工作流无缝衔接
- **多语言支持** — English、简体中文、繁體中文、日本語，自动跟随浏览器语言
- **WebSocket 二进制协议** — 高效的低延迟通信，自定义二进制帧
- **oh-my-zsh 支持** — 完全兼容主题、插件和自动补全
- **会话持久化** — 重新连接到运行中的会话，不丢失状态
- **审计日志** — 跟踪所有用户操作，满足合规和安全要求
- **文件管理** — 通过终端界面上传和下载文件
- **JWT 认证** — 基于令牌的安全访问
- **一键部署** — 使用 Docker 或单个 shell 脚本运行

## 系统架构

```text
浏览器 (xterm.js)
    │
    │  HTTPS / WSS
    ▼
FastAPI 后端
    ├── REST API (认证、会话、文件、审计)
    └── WebSocket 处理器 (二进制协议)
            │
            ▼
        PTY 运行时
            │
            ├── bash
            ├── zsh (oh-my-zsh)
            └── fish
```

**技术栈**

| 层级   | 技术                                           |
| ------ | ---------------------------------------------- |
| 前端   | Vue 3 (Composition API)、Pinia、xterm.js v5    |
| 后端   | FastAPI、SQLAlchemy (async)、aiosqlite         |
| 终端   | Python PTY (pty.fork)、login shell             |
| 数据库 | SQLite (默认)，支持 PostgreSQL                 |
| 认证   | JWT with RSA、bcrypt 密码哈希                  |

## 快速开始

**前置要求：** Python 3.12+、Node.js 18+、npm

```bash
# 前端
cd frontend
npm install
npm run build

# 后端
cd ../backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 启动（同时提供 API 和前端服务）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

打开 `http://localhost:8000` 并注册第一个账户。

### Shell 脚本

```bash
./deploy.sh
```

这会自动安装依赖、构建前端并在端口 8000 启动服务器。

停止服务器：

```bash
./deploy.sh --stop
```

### Docker

```bash
docker compose up -d
```

打开 `http://localhost:8000` 并注册第一个账户。

## 配置说明

所有设置通过环境变量配置（前缀：`WEBTTY_`）：

| 变量                                 | 默认值                             | 说明                                 |
| ------------------------------------ | ---------------------------------- | ------------------------------------ |
| `WEBTTY_SECRET_KEY`                  | 自动生成                           | JWT 签名密钥。**生产环境必须设置。** |
| `WEBTTY_DATABASE_URL`                | `sqlite+aiosqlite:///./webtty.db`  | 数据库连接字符串                     |
| `WEBTTY_STATIC_DIR`                  | 自动检测                           | 前端构建输出路径                     |
| `WEBTTY_UPLOAD_DIR`                  | `./uploads`                        | 上传文件目录                         |
| `WEBTTY_ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                               | JWT 访问令牌有效期                   |
| `WEBTTY_REFRESH_TOKEN_EXPIRE_DAYS`   | `7`                                | JWT 刷新令牌有效期                   |
| `WEBTTY_MAX_UPLOAD_SIZE`             | `104857600`                        | 最大上传大小（字节，100MB）          |

### 生产环境示例

```bash
export WEBTTY_SECRET_KEY="your-random-secret-string"
export WEBTTY_DATABASE_URL="sqlite+aiosqlite:////data/webtty.db"
./deploy.sh
```

## 项目结构

```text
web-terminal/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── config.py            # 设置和环境变量
│   │   ├── database.py          # SQLAlchemy 异步会话工厂
│   │   ├── models.py            # 数据库模型 (User, Session 等)
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── auth/                # 认证模块
│   │   │   ├── router.py        #   登录、注册、刷新端点
│   │   │   ├── service.py       #   JWT 令牌生成和验证
│   │   │   └── dependencies.py  #   受保护路由的认证依赖
│   │   ├── session/             # 会话管理模块
│   │   │   ├── router.py        #   会话 CRUD 端点
│   │   │   └── service.py       #   会话生命周期逻辑
│   │   ├── terminal/            # 终端运行时模块
│   │   │   ├── host_runtime.py  #   PTY 进程管理 (pty.fork)
│   │   │   ├── runtime.py       #   抽象运行时接口
│   │   │   ├── manager.py       #   会话管理器和重连
│   │   │   ├── ws_handler.py    #   WebSocket 处理器 (二进制协议)
│   │   │   └── router.py        #   WebSocket 端点注册
│   │   ├── file/                # 文件管理模块
│   │   │   └── router.py        #   上传/下载端点
│   │   └── audit/               # 审计日志模块
│   │       ├── router.py        #   审计查询端点
│   │       └── service.py       #   审计事件记录
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.js              # Vue 应用入口
│   │   ├── App.vue              # 根组件
│   │   ├── router/              # Vue Router 配置
│   │   ├── stores/              # Pinia 状态管理
│   │   │   ├── auth.js          #   认证状态和令牌管理
│   │   │   └── terminal.js      #   会话和标签页状态
│   │   ├── i18n/                # 国际化配置
│   │   │   ├── index.js         #   i18n 初始化和语言检测
│   │   │   └── locales/         #   语言文件 (en-US, zh-CN, zh-TW, ja)
│   │   ├── services/
│   │   │   ├── api.js           #   Axios HTTP 客户端
│   │   │   └── terminal-ws.js   #   WebSocket 客户端 (二进制协议)
│   │   ├── components/
│   │   │   ├── layout/          #   UI 布局组件
│   │   │   │   ├── StatusBar.vue
│   │   │   │   ├── SplitPane.vue
│   │   │   │   └── TerminalToolbar.vue
│   │   │   └── terminal/        #   终端相关组件
│   │   │       ├── TerminalPane.vue   # xterm.js 封装
│   │   │       └── TerminalTabs.vue   # 多标签页 UI
│   │   ├── views/               # 页面级组件
│   │   │   ├── LoginView.vue
│   │   │   ├── SettingsView.vue
│   │   │   └── TerminalView.vue
│   │   └── styles/
│   │       └── global.css
│   ├── package.json
│   └── vite.config.js
├── Dockerfile                   # 多阶段 Docker 构建
├── docker-compose.yml           # Docker Compose 配置
├── deploy.sh                    # 一键部署脚本
├── .dockerignore
├── .gitignore
├── prd.md                       # 产品需求文档
└── design.md                    # 技术设计规范
```

## WebSocket 协议

终端使用自定义二进制协议提高效率：

```text
┌─────────┬────────────┬─────────┐
│ opcode  │  length    │ payload │
│ (1 字节) │ (4 字节)   │ (N 字节) │
└─────────┴────────────┴─────────┘
```

| 操作码 | 名称      | 方向             | 说明         |
| ------ | --------- | ---------------- | ------------ |
| `0x01` | INPUT     | 客户端 → 服务器  | 键盘输入     |
| `0x02` | OUTPUT    | 服务器 → 客户端  | 终端输出     |
| `0x03` | RESIZE    | 客户端 → 服务器  | 窗口大小变化 |
| `0x04` | HEARTBEAT | 双向             | 心跳 ping    |
| `0x05` | CLOSE     | 双向             | 优雅关闭     |
| `0x06` | ERROR     | 服务器 → 客户端  | 错误消息     |

## API 参考

### 认证

| 方法 | 端点                     | 说明                |
| ---- | ------------------------ | ------------------- |
| POST | `/api/auth/register`     | 创建新用户账户      |
| POST | `/api/auth/login`        | 认证并获取 JWT 令牌 |
| POST | `/api/auth/refresh`      | 刷新访问令牌        |

### 会话

| 方法   | 端点                            | 说明               |
| ------ | ------------------------------- | ------------------ |
| GET    | `/api/sessions`                 | 列出所有会话       |
| POST   | `/api/sessions`                 | 创建新终端会话     |
| POST   | `/api/sessions/{id}/reconnect`  | 重新连接到现有会话 |
| DELETE | `/api/sessions/{id}`            | 删除会话           |

### 终端

| 方法      | 端点                            | 说明                |
| --------- | ------------------------------- | ------------------- |
| WebSocket | `/api/terminal/ws/{session_id}` | 终端 WebSocket 连接 |

### 健康检查

| 方法 | 端点          | 说明         |
| ---- | ------------- | ------------ |
| GET  | `/api/health` | 健康检查端点 |

## 开发

```bash
# 终端 1：后端热重载
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# 终端 2：前端开发服务器，带 API 代理
cd frontend
npm run dev
```

前端开发服务器运行在 `http://localhost:3000`，并将 `/api` 请求代理到后端。

## 许可证

MIT
