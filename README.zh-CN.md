# MebTTY

<p align="center">
  <strong>一个自托管的 Web 终端，将服务器的完整能力带到任意浏览器。</strong><br>
  <em>MebTTY = MebTTY Makes Browsers TTY.</em><br>
  打开标签页，选择 shell，即刻开始工作 —— 无需 SSH 客户端，无需配置，零摩擦。
</p>

<p align="center">
  <a href="README.md">English</a> | <strong>简体中文</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blueviolet" alt="Version">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/vue-3.4%2B-brightgreen?logo=vue.js&logoColor=white" alt="Vue">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
</p>

---

MebTTY 将任意现代浏览器变成全功能终端。基于 **FastAPI** 和 **Vue 3** 构建，提供真正的 PTY 会话，支持 bash、zsh、fish、nushell 等多种 shell —— 包括 oh-my-zsh 主题和 vim、htop、less 等交互式 TUI 程序。

内置的**文件浏览器**让你在终端旁浏览、预览、编辑、上传、下载、重命名和删除文件。**Catppuccin 主题**的 UI 支持深色/浅色模式、自定义强调色、多标签页，以及四种语言（English、简体中文、繁體中文、日本語），让日常使用更加愉悦。

通过单个脚本或 Docker 一键部署 —— 随时随地访问你的服务器。

## 功能特性

### 终端

- **完整的 PTY 支持** — 通过 `pty.fork()` 实现真正的伪终端，以登录 shell 方式启动；支持 bash、zsh、fish、nushell 等
- **动态 Shell 检测** — 自动从 `/etc/shells` 和 PATH 发现可用 shell，配有品牌 SVG 图标
- **交互式程序** — vim、less、top、htop 等所有 TUI 应用完美运行
- **oh-my-zsh 兼容** — 完全支持主题、插件和自动补全
- **会话持久化** — 断开后可重新连接到运行中的会话，不丢失状态；会话在服务重启后存活
- **自定义二进制 WebSocket 协议** — 高效的低延迟终端 I/O，带心跳保活
- **xterm.js 驱动** — 256 色支持、5000 行回滚、搜索、可点击 URL、Unicode 11

### 多标签页界面

- **多会话** — 在单个窗口中打开和切换多个终端会话
- **标签页管理** — 创建、关闭、重命名（双击）和拖拽排序标签页
- **设置页标签化** — 设置页面作为标签页打开，工作流无缝衔接
- **自定义标签页标题** — 基于模板的标题，支持 `{shell}`、`{index}`、`{title}`、`{user}`、`{cwd}` 变量
- **实时工作目录标题** — `{cwd}` 跟随 shell 当前目录变化，家目录显示为 `~`，其他路径只显示最后一级目录名
- **动态浏览器标题** — 窗口标题随活动会话自动更新

### 文件浏览器

- **侧边栏浏览器** — 可切换显示、可调整宽度的侧边栏，带目录树视图和面包屑导航
- **完整文件操作** — 浏览、上传、下载、创建目录、重命名和删除文件
- **内联预览与编辑器** — 双击文本文件，在终端旁打开可调整宽度的编辑面板
- **默认自动保存** — 文本编辑默认自动保存，也支持手动保存和未保存变更保护
- **只读媒体预览** — 图片以预览方式打开；不支持编辑的非文本文件只展示元信息
- **可选行号** — 可在设置中开启文件编辑器行号
- **Catppuccin 文件图标** — 200+ 主题化 SVG 文件和文件夹图标
- **右键菜单** — 右键点击快速执行文件操作
- **可配置根目录** — 通过环境变量设置浏览根目录
- **路径遍历保护** — 所有文件路径经过验证，确保在允许的根目录内

### 外观与自定义

- **Catppuccin 配色方案** — Mocha（深色）和 Latte（浅色）调色板，同时应用于 UI 和终端
- **三种主题模式** — 跟随系统、深色和浅色
- **自定义强调色** — 7 种预设色（紫罗兰、蓝、翡翠、琥珀、红、粉、青）加自定义取色器
- **可配置状态栏** — 显示/隐藏、拖拽排序项目（shell、进程状态、连接状态），左右定位
- **侧边栏位置** — 选择文件浏览器在左侧或右侧

### 国际化

- **四种语言** — English、简体中文、繁體中文、日本語
- **浏览器自动检测** — 匹配 `navigator.language`，带前缀回退
- **持久化偏好** — 同时保存到 localStorage 和服务端用户设置

### 安全与管理

- **JWT 认证** — 基于令牌的认证，支持访问/刷新令牌轮换和 bcrypt 密码哈希
- **自动刷新令牌** — 访问令牌过期时自动使用刷新令牌续期，失败后才跳转登录
- **用户头像** — 上传和显示头像（PNG、JPEG、WebP、GIF）
- **审计日志** — 跟踪所有用户操作和执行的命令，带风险等级
- **管理员控制** — 仅管理员可查看审计事件列表；按用户隔离访问
- **密码管理** — 通过当前密码验证后修改密码

### 部署与运维

- **一键部署** — 单个 shell 脚本完成依赖检查、构建和服务器启动
- **可重复部署** — 修改代码后可直接重复运行 `./deploy.sh` 或 `./deploy.sh --docker`，自动重建并替换当前实例
- **独立可执行程序** — 使用 PyInstaller 构建单个 Linux 二进制文件，安装为 systemd 服务，带安全加固和自动重启
- **Docker 支持** — 多阶段构建，持久化卷和自动重启
- **会话自动清理** — 服务重启时清理过期会话；按可配置超时自动删除过期会话
- **数据库灵活性** — 默认 SQLite，生产环境支持 PostgreSQL

## 系统架构

```text
浏览器 (xterm.js)
    │
    │  HTTPS / WSS
    ▼
FastAPI 后端
    ├── REST API (认证、会话、文件、设置、审计)
    └── WebSocket 处理器 (二进制协议)
            │
            ▼
        PTY 运行时
            │
            ├── bash
            ├── zsh (oh-my-zsh)
            ├── fish
            ├── nushell
            └── sh / dash / ksh / csh / tcsh
```

**技术栈**

| 层级   | 技术                                           |
| ------ | ---------------------------------------------- |
| 前端   | Vue 3 (Composition API)、Pinia、xterm.js v5    |
| 后端   | FastAPI、SQLAlchemy (async)、aiosqlite / asyncpg |
| 终端   | Python PTY (`pty.fork`)、login shell           |
| 数据库 | SQLite (默认)，支持 PostgreSQL                 |
| 认证   | JWT (HS256)、bcrypt 密码哈希                   |
| 国际化 | vue-i18n，浏览器语言自动检测                   |

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
python -m uvicorn app.main:app --host 0.0.0.0 --port 18888
```

打开 `http://localhost:18888` 并注册第一个账户。

### Shell 脚本

```bash
./deploy.sh
```

这会自动安装依赖、构建前端并在端口 18888 启动服务器。
修改代码后可以直接重复运行该命令，脚本会替换当前正在运行的实例。

```bash
./deploy.sh --status     # 查看服务器状态
./deploy.sh --stop       # 停止服务器
./deploy.sh --restart    # 重启服务器
./deploy.sh --logs       # 查看日志
./deploy.sh --update     # 拉取最新代码并重新部署
./deploy.sh --docker     # 通过 Docker Compose 部署
./deploy.sh --help       # 查看所有命令
```

### Docker

```bash
docker compose up -d
```

打开 `http://localhost:18888` 并注册第一个账户。

### 独立可执行程序（systemd 服务）

构建包含前后端的单个自包含二进制文件，然后安装为 systemd 系统服务。

**前置要求：** Python 3.12+、Node.js 18+、npm

```bash
# 构建：编译前端并打包为单个可执行文件
./build.sh

# 安装：复制二进制、创建数据目录、生成配置、注册 systemd 服务
sudo ./install.sh
```

安装后，MebTTY 作为受管理的 systemd 服务运行，带有安全加固（`ProtectSystem=strict`、`NoNewPrivileges`、`PrivateTmp`）和故障自动重启。

```bash
sudo systemctl start mebtty      # 启动服务
sudo systemctl stop mebtty       # 停止服务
sudo systemctl restart mebtty    # 重启服务
sudo systemctl status mebtty     # 查看服务状态
sudo journalctl -u mebtty -f     # 查看日志
```

| 路径                              | 说明                         |
| --------------------------------- | ---------------------------- |
| `/usr/local/bin/mebtty`           | 可执行文件                   |
| `/etc/mebtty/mebtty.env`          | 环境配置（自动生成）         |
| `/var/lib/mebtty/mebtty.db`       | SQLite 数据库                |
| `/var/lib/mebtty/uploads`         | 上传文件目录                 |

```bash
# 卸载（移除服务和二进制文件，保留数据和配置）
sudo ./install.sh --uninstall
```

## 配置说明

所有设置通过环境变量配置（前缀：`MEBTTY_`）：

| 变量                                 | 默认值                             | 说明                                 |
| ------------------------------------ | ---------------------------------- | ------------------------------------ |
| `MEBTTY_SECRET_KEY`                  | 自动生成                           | JWT 签名密钥。**生产环境必须设置。** |
| `MEBTTY_DATABASE_URL`                | `sqlite+aiosqlite:///./mebtty.db`  | 数据库连接字符串                     |
| `MEBTTY_BROWSE_ROOT`                 | `~`（用户主目录）                  | 文件浏览器根目录                     |
| `MEBTTY_STATIC_DIR`                  | 自动检测                           | 前端构建输出路径                     |
| `MEBTTY_UPLOAD_DIR`                  | `./uploads`                        | 上传文件和头像目录                   |
| `MEBTTY_ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                               | JWT 访问令牌有效期                   |
| `MEBTTY_REFRESH_TOKEN_EXPIRE_DAYS`   | `7`                                | JWT 刷新令牌有效期                   |
| `MEBTTY_MAX_UPLOAD_SIZE`             | `104857600`                        | 最大上传大小（字节，100MB）          |
| `MEBTTY_HOST`                        | `0.0.0.0`                          | 服务器绑定地址                       |
| `MEBTTY_PORT`                        | `18888`                            | 服务器监听端口                       |

### 生产环境示例

```bash
export MEBTTY_SECRET_KEY="your-random-secret-string"
export MEBTTY_DATABASE_URL="sqlite+aiosqlite:////data/mebtty.db"
./deploy.sh
```

## 项目结构

```text
mebtty/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── config.py            # 设置和环境变量
│   │   ├── database.py          # SQLAlchemy 异步会话工厂
│   │   ├── models.py            # 数据库模型 (User, Session 等)
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── auth/                # 认证模块
│   │   │   ├── router.py        #   登录、注册、刷新、头像端点
│   │   │   ├── service.py       #   JWT 令牌生成和验证
│   │   │   └── dependencies.py  #   受保护路由的认证依赖
│   │   ├── session/             # 会话管理模块
│   │   │   ├── router.py        #   CRUD 端点和 shell 检测
│   │   │   └── service.py       #   会话生命周期逻辑
│   │   ├── terminal/            # 终端运行时模块
│   │   │   ├── host_runtime.py  #   PTY 进程管理 (pty.fork)
│   │   │   ├── runtime.py       #   抽象运行时接口
│   │   │   ├── manager.py       #   会话管理器和重连
│   │   │   ├── ws_handler.py    #   WebSocket 处理器 (二进制协议)
│   │   │   └── router.py        #   WebSocket 端点注册
│   │   ├── file/                # 文件管理模块
│   │   │   └── router.py        #   浏览、上传、下载、创建目录、重命名、删除
│   │   ├── settings/            # 用户设置模块
│   │   │   └── router.py        #   获取/更新用户偏好
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
│   │   │   ├── terminal.js      #   会话和标签页状态
│   │   │   ├── theme.js         #   主题模式和强调色
│   │   │   └── settings.js      #   用户偏好
│   │   ├── i18n/                # 国际化
│   │   │   ├── index.js         #   i18n 初始化和浏览器语言检测
│   │   │   └── locales/         #   语言文件 (en-US, zh-CN, zh-TW, ja)
│   │   ├── services/
│   │   │   ├── api.js           #   Axios HTTP 客户端
│   │   │   └── terminal-ws.js   #   WebSocket 客户端 (二进制协议)
│   │   ├── components/
│   │   │   ├── layout/          #   UI 布局组件
│   │   │   │   ├── StatusBar.vue
│   │   │   │   └── SplitPane.vue
│   │   │   ├── terminal/        #   终端相关组件
│   │   │   │   ├── TerminalPane.vue   # xterm.js 封装
│   │   │   │   ├── TerminalTabs.vue   # 多标签页 UI
│   │   │   │   ├── FileBrowser.vue    # 侧边栏文件浏览器
│   │   │   │   └── FileEditorPane.vue # 文件预览和文本编辑器
│   │   │   └── common/
│   │   │       └── ThemeToggle.vue    # 主题模式切换器
│   │   ├── views/               # 页面级组件
│   │   │   ├── LoginView.vue
│   │   │   ├── HomeView.vue
│   │   │   ├── TerminalView.vue
│   │   │   └── SettingsView.vue
│   │   └── styles/
│   │       └── global.css
│   ├── package.json
│   └── vite.config.js
├── build.sh                     # 构建独立可执行文件 (PyInstaller)
├── install.sh                   # 安装/卸载 systemd 服务
├── mebtty.service               # systemd 服务单元文件
├── Dockerfile                   # 多阶段 Docker 构建
├── docker-compose.yml           # Docker Compose 配置
├── deploy.sh                    # 一键部署脚本
├── .dockerignore
└── .gitignore
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
| `0x07` | CWD       | 服务器 → 客户端  | 当前工作目录 |

## API 参考

### 认证

| 方法 | 端点                            | 说明                |
| ---- | ------------------------------- | ------------------- |
| POST | `/api/auth/register`            | 创建新用户账户      |
| POST | `/api/auth/login`               | 认证并获取 JWT 令牌 |
| POST | `/api/auth/refresh`             | 刷新访问令牌        |
| GET  | `/api/auth/me`                  | 获取当前用户信息    |
| POST | `/api/auth/change-password`     | 修改账户密码        |
| POST | `/api/auth/avatar`              | 上传头像            |
| GET  | `/api/auth/avatar/{filename}`   | 获取头像文件        |

### 会话

| 方法   | 端点                            | 说明               |
| ------ | ------------------------------- | ------------------ |
| GET    | `/api/sessions`                 | 列出所有会话       |
| POST   | `/api/sessions`                 | 创建新终端会话     |
| GET    | `/api/sessions/shells`          | 列出可用 shell     |
| GET    | `/api/sessions/{id}`            | 获取特定会话       |
| POST   | `/api/sessions/{id}/reconnect`  | 重新连接到现有会话 |
| DELETE | `/api/sessions/{id}`            | 删除会话           |

### 终端

| 方法      | 端点                            | 说明                |
| --------- | ------------------------------- | ------------------- |
| WebSocket | `/api/terminal/ws/{session_id}` | 终端 WebSocket 连接 |

### 文件

| 方法 | 端点                         | 说明               |
| ---- | ---------------------------- | ------------------ |
| GET  | `/api/files/browse`          | 浏览目录内容       |
| POST | `/api/files/upload-browse`   | 上传文件到目录     |
| GET  | `/api/files/download-browse` | 下载文件           |
| GET  | `/api/files/read`            | 读取文本文件用于编辑 |
| PUT  | `/api/files/write`           | 保存文本文件       |
| POST | `/api/files/mkdir`           | 创建新目录         |
| POST | `/api/files/rename`          | 重命名文件或目录   |
| POST | `/api/files/delete`          | 删除文件或目录     |
| POST | `/api/files/upload`          | 上传文件到会话     |
| GET  | `/api/files/download`        | 从会话下载文件     |
| GET  | `/api/files/list`            | 列出会话中的文件   |

### 设置

| 方法 | 端点            | 说明             |
| ---- | --------------- | ---------------- |
| GET  | `/api/settings` | 获取用户设置     |
| PUT  | `/api/settings` | 更新用户设置     |

### 审计

| 方法 | 端点                               | 说明                        |
| ---- | ---------------------------------- | --------------------------- |
| GET  | `/api/audit/commands/{session_id}` | 列出会话的命令              |
| GET  | `/api/audit/events`                | 列出所有审计事件（仅管理员）|
| GET  | `/api/audit/events/{user_id}`      | 列出用户的审计事件          |

### 健康检查

| 方法 | 端点          | 说明         |
| ---- | ------------- | ------------ |
| GET  | `/api/health` | 健康检查端点 |

## 开发

```bash
# 终端 1：后端热重载
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 18888

# 终端 2：前端开发服务器，带 API 代理
cd frontend
npm run dev
```

前端开发服务器运行在 `http://localhost:3000`，并将 `/api` 请求代理到后端。

## 开源项目与第三方声明

MebTTY 基于多个开源项目构建，并随仓库分发少量资源文件。下表列出正常使用和再分发时最需要关注的主要直接依赖与资源。间接依赖以各生态生成的锁文件和包元数据为准。

### 后端

| 项目 | 用途 | 许可证 |
| ---- | ---- | ------ |
| [FastAPI](https://fastapi.tiangolo.com/) | HTTP API 框架 | MIT |
| [Uvicorn](https://www.uvicorn.org/) | ASGI 服务器 | BSD-3-Clause |
| [SQLAlchemy](https://www.sqlalchemy.org/) | ORM 与数据库访问 | MIT |
| [Alembic](https://alembic.sqlalchemy.org/) | 数据库迁移 | MIT |
| [Pydantic](https://docs.pydantic.dev/) / [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | 数据校验与配置管理 | MIT |
| [python-jose](https://github.com/mpdavis/python-jose) | JWT 处理 | MIT |
| [passlib](https://passlib.readthedocs.io/) / [bcrypt](https://github.com/pyca/bcrypt) | 密码哈希工具 | BSD / Apache-2.0 |
| [python-multipart](https://github.com/Kludex/python-multipart) | multipart 表单解析与上传 | Apache-2.0 |
| [aiofiles](https://github.com/Tinche/aiofiles) | 异步文件 I/O | Apache-2.0 |
| [websockets](https://websockets.readthedocs.io/) | WebSocket 协议支持 | BSD-3-Clause |
| [aiosqlite](https://aiosqlite.omnilib.dev/) | 异步 SQLite 访问 | MIT |
| [redis-py](https://redis.readthedocs.io/) | Redis 客户端支持 | MIT |

### 前端

| 项目 | 用途 | 许可证 |
| ---- | ---- | ------ |
| [Vue](https://vuejs.org/) | UI 框架 | MIT |
| [Vue Router](https://router.vuejs.org/) | 客户端路由 | MIT |
| [Pinia](https://pinia.vuejs.org/) | 应用状态管理 | MIT |
| [vue-i18n](https://vue-i18n.intlify.dev/) | 国际化 | MIT |
| [Axios](https://axios-http.com/) | HTTP 客户端 | MIT |
| [xterm.js](https://xtermjs.org/) 及插件 | 浏览器终端模拟器 | MIT |
| [Split.js](https://split.js.org/) | 可调整宽度的分屏布局 | MIT |
| [vscode-icon-resolver](https://github.com/DevYatsu/file-extension-icon) | 文件图标名称解析 | MIT |
| [Vite](https://vite.dev/) / [@vitejs/plugin-vue](https://github.com/vitejs/vite-plugin-vue) | 前端构建工具 | MIT |

### 随仓库分发的资源

| 资源 | 用途 | 许可证 / 声明 |
| ---- | ---- | ------------- |
| Noto Sans | UI 字体 | Apache-2.0，见 [`frontend/src/assets/fonts/NotoSans-OFL.txt`](frontend/src/assets/fonts/NotoSans-OFL.txt) |
| JetBrains Mono Nerd Font | 终端字体 | SIL Open Font License 1.1，见 [`frontend/src/assets/fonts/JetBrainsMonoNLNerdFont-OFL.txt`](frontend/src/assets/fonts/JetBrainsMonoNLNerdFont-OFL.txt) |
| [Catppuccin Icons for VSCode](https://github.com/catppuccin/vscode-icons) | 文件与文件夹图标 | MIT，随仓库分发的 SVG 资源位于 [`frontend/public/catppuccin-icons/`](frontend/public/catppuccin-icons/) |

更新依赖或替换随仓库分发的资源时，请保留相应上游项目的版权声明和许可证条款。

## 许可证

MebTTY 基于 MIT License 发布。完整许可证文本见 [`LICENSE`](LICENSE)。

除非另有说明，本项目作者编写的源代码均按 MIT License 授权。第三方依赖与随仓库分发的资源仍遵循各自上游许可证。本节用于为用户和再分发者提供清晰的实践性说明，不替代上游项目自带的原始许可证文本。
