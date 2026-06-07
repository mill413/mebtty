你现在已经进入 **LLD（Low Level Design）+ HLD（High Level Design）融合阶段** 了。

如果这个项目最终目标是：

> 企业级 Web Terminal 平台（对标 GitHub Codespaces Terminal、VSCode Remote Terminal、JumpServer Terminal）

那么我建议不要再以「WebSocket + PTY」的思维设计，而是直接按照：

```text
Terminal as a Service (TaaS)
```

设计。

否则未来支持：

* Docker
* Kubernetes
* SSH资产
* 终端录制
* 多人协同
* AI Agent

时一定会推翻重构。

下面这份文档是我认为比较合理的 **V1~V3 可演进架构**。

---

# 1. 总体架构

```text
                                ┌──────────────┐
                                │    Browser   │
                                └──────┬───────┘
                                       │
                                       │ HTTPS / WSS
                                       ▼
┌─────────────────────────────────────────────────────────┐
│                    Terminal Gateway                      │
│                                                         │
│ JWT                                                     │
│ Session Routing                                         │
│ WebSocket Multiplex                                     │
│ Rate Limit                                              │
└──────────────┬──────────────────────────────────────────┘
               │
               │ gRPC
               │
     ┌─────────┴─────────┐
     ▼                   ▼

Session Service      Runtime Service

     ▼                   ▼

PostgreSQL       Runtime Scheduler

                         ▼

          ┌──────────────┼──────────────┐
          ▼              ▼              ▼

     HostRuntime   DockerRuntime   K8sRuntime

          ▼              ▼              ▼

         PTY            PTY            PTY

          ▼              ▼              ▼

         bash           zsh           fish
```

---

# 2. 服务拆分

## gateway

唯一公网入口

职责：

```text
JWT鉴权

WebSocket升级

连接管理

Session绑定

流量转发
```

不允许直接操作PTY。

---

## session-service

职责：

```text
创建会话

销毁会话

恢复会话

查询会话

会话状态同步
```

数据库唯一可信来源。

---

## runtime-service

整个系统核心。

职责：

```text
启动Runtime

关闭Runtime

监控Runtime

负载均衡

调度Runtime
```

---

## audit-service

负责：

```text
输入审计

输出审计

录像

敏感命令检测
```

---

## storage-service

负责：

```text
录像存储

上传文件

下载文件

对象存储
```

---

## auth-service

负责：

```text
登录

用户

RBAC

权限校验
```

---

# 3. Runtime抽象层

不要把PTY写死。

定义：

```python
class Runtime(ABC):

    async def start()

    async def stop()

    async def write()

    async def resize()

    async def read()
```

---

实现：

```python
HostRuntime

DockerRuntime

KubernetesRuntime

SSHRuntime
```

---

这样未来扩展：

```text
Pod终端
SSH终端
DevContainer
```

不需要改Gateway。

---

# 4. Runtime Manager

## 类结构

```python
class RuntimeManager:

    runtimes: dict[str, Runtime]

    async def create_runtime()

    async def get_runtime()

    async def destroy_runtime()
```

---

内存：

```python
{
  session_id: Runtime
}
```

---

# 5. PTY模块设计

目录：

```text
runtime/
├── pty/
│   ├── driver.py
│   ├── reader.py
│   ├── writer.py
│   ├── resize.py
│   └── signal.py
```

---

## PTY Driver

职责：

```text
创建PTY

绑定Shell

管理FD
```

---

```python
class PtyDriver:

    master_fd

    slave_fd

    pid
```

---

启动：

```python
pid, fd = pty.fork()
```

---

# 6. Shell启动器

```python
class ShellLauncher:
```

职责：

```text
选择shell

设置环境变量

执行shell
```

---

环境变量：

```bash
TERM=xterm-256color

COLORTERM=truecolor

LANG=en_US.UTF-8

LC_ALL=en_US.UTF-8

SHELL=/usr/bin/zsh
```

---

执行：

```python
os.execve(
 shell,
 [shell],
 env
)
```

---

# 7. Terminal Session

数据库：

```sql
terminal_session
```

---

结构：

```sql
id uuid

user_id uuid

runtime_type varchar

runtime_id varchar

shell varchar

status varchar

cols integer

rows integer

created_at timestamptz
```

---

状态机：

```text
CREATED

↓

STARTING

↓

RUNNING

↓

DETACHED

↓

REATTACHED

↓

STOPPED

↓

DESTROYED
```

---

# 8. Redis设计

## Session索引

```text
terminal:session:{id}
```

---

值：

```json
{
  "runtime_id":"abc",
  "node":"worker-01"
}
```

---

## 用户会话

```text
user:sessions:{user_id}
```

---

```json
[
  "session1",
  "session2"
]
```

---

# 9. WebSocket协议

不要JSON。

直接二进制。

---

包头：

```c
struct Packet {

 uint8 opcode;

 uint32 length;

 bytes payload;
}
```

---

# Opcode

```text
0x01 INPUT

0x02 OUTPUT

0x03 RESIZE

0x04 HEARTBEAT

0x05 CLOSE

0x06 ERROR

0x07 CLIPBOARD

0x08 FILE_UPLOAD
```

---

# INPUT

```text
0x01

payload:
ls -la\n
```

---

# OUTPUT

```text
0x02

payload:
shell output
```

---

# RESIZE

```text
0x03

payload:

cols:uint16

rows:uint16
```

---

# 10. 前端架构

目录：

```text
src/

components/

terminal/

store/

services/

pages/

layouts/
```

---

# Terminal组件树

```text
TerminalPage

 ├─ TerminalToolbar

 ├─ TerminalTabs

 ├─ SplitContainer

 │    ├─ TerminalPane
 │    ├─ TerminalPane
 │
 └─ StatusBar
```

---

# TerminalPane

内部：

```text
xterm.js

FitAddon

WebGLAddon

SearchAddon

UnicodeAddon
```

---

# Terminal对象

```typescript
class TerminalSession {

 sessionId:string

 terminal:Terminal

 socket:WebSocket
}
```

---

# 11. 多标签实现

Pinia：

```typescript
state:

tabs:[]
```

---

结构：

```typescript
{
 id:string

 title:string

 active:boolean
}
```

---

# 12. 分屏实现

推荐：

```text
GoldenLayout
```

或者：

```text
Split.js
```

---

数据结构：

```json
{
  "direction":"horizontal",
  "children":[]
}
```

---

# 13. 文件上传

协议：

```text
Browser

↓

Chunk Upload

↓

Gateway

↓

Storage Service

↓

MinIO
```

---

分片：

```text
4MB
```

---

支持：

```text
断点续传

秒传

MD5校验
```

---

# 14. 文件下载

禁止：

```bash
cat huge.log
```

---

增加：

```text
Download API
```

---

```http
GET /api/files/download
```

---

# 15. 终端录像

核心：

记录字节流。

---

结构：

```json
{
 "timestamp":123456,
 "type":"output",
 "data":"..."
}
```

---

保存：

```text
asciinema格式
```

优势：

* 体积小
* 可回放
* 可搜索

---

# 16. Docker Runtime

## 创建容器

```bash
docker run
```

---

镜像：

```text
webtty-runtime
```

---

预装：

```text
bash

zsh

fish

tmux

vim

neovim

git

kubectl

docker-cli
```

---

# 17. Kubernetes Runtime

结构：

```text
Runtime Service

↓

Kubernetes API

↓

Pod

↓

Container

↓

PTY
```

---

每个Session：

```text
1 Pod
```

或者：

```text
1 User
1 Pod
```

---

# 18. 审计系统

## 命令检测

匹配：

```bash
rm -rf

shutdown

mkfs

dd if=
```

---

记录：

```json
{
 "user":"admin",
 "command":"rm -rf /"
}
```

---

风险等级：

```text
LOW

MEDIUM

HIGH

CRITICAL
```

---

# 19. 性能目标

单节点：

```text
8 Core

16GB
```

目标：

```text
3000+
PTY
```

---

WebSocket：

```text
10000+
连接
```

---

输入延迟：

```text
<20ms
```

---

输出延迟：

```text
<50ms
```

---

# 20. V2 架构预留

必须提前预留接口。

未来扩展：

```text
AI命令解释

AI日志分析

AI错误修复

AI终端助手
```

因此 Runtime 输出流最好设计为事件总线：

```text
PTY

↓

EventBus

↓

Gateway

↓

Audit

↓

AI Agent

↓

Recorder
```

而不是直接：

```text
PTY -> WebSocket
```

因为未来录像、审计、AI 都需要消费同一份终端字节流。

---

如果继续往下做，下一层已经不是设计文档，而是 **代码级架构设计** 了，包括：

* 完整 FastAPI 项目目录结构（约 200+ 文件）
* SQLAlchemy ORM 模型
* Alembic 迁移方案
* RuntimeManager 实现
* PtyDriver 实现
* WebSocket 二进制协议 SDK
* Vue3 + Pinia + xterm.js 代码结构
* Docker Runtime 镜像设计
* Kubernetes Operator 设计
* 单机 1 万终端连接优化方案（epoll + uvloop + 零拷贝）

这些内容已经接近“技术方案书 + 开发蓝图”级别。
