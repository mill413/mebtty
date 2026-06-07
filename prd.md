# Web Terminal 平台产品需求文档（PRD）

Version: v1.0

Product Name: WebTTY Enterprise

Owner: Platform Team

Target Release: MVP v1.0

---

# 1. 产品背景

## 1.1 问题描述

当前运维、开发和数据工程师主要通过：

* SSH Client
* Putty
* SecureCRT
* MobaXterm
* iTerm2
* Konsole
* GNOME Terminal

访问服务器。

存在问题：

### 运维管理复杂

用户需要：

* 保存 SSH 配置
* 管理密钥
* 管理跳板机

学习成本高。

### 无统一审计

无法记录：

* 用户输入
* 文件操作
* 会话过程

存在安全风险。

### 多终端环境割裂

开发环境：

* 本地终端

测试环境：

* SSH

生产环境：

* 堡垒机

体验不一致。

### 无法通过浏览器直接访问

用户必须安装客户端。

---

# 1.2 产品目标

建设统一浏览器终端平台。

实现：

Browser ⇄ WebSocket ⇄ PTY ⇄ Shell

支持：

* Linux
* Docker
* Kubernetes

实现：

* 零客户端
* 真实终端
* 完整TUI支持
* 企业级审计
* 多租户隔离

---

# 2. 产品定位

## 核心定位

企业级 Web Terminal 平台

对标：

* VSCode Terminal
* GitHub Codespaces
* Gitpod
* JumpServer Terminal
* ttyd
* Wetty

---

# 3. 用户角色

## 普通开发者

权限：

* 登录
* 创建终端
* 文件上传
* 文件下载

---

## 运维工程师

权限：

* SSH管理
* 主机管理
* 容器管理

---

## 管理员

权限：

* 用户管理
* 审计管理
* 权限管理
* 系统配置

---

# 4. 产品架构

Browser

↓

Terminal Gateway

↓

Session Service

↓

PTY Service

↓

Shell Runtime

↓

Linux System

---

# 5. 功能需求

# 5.1 用户认证

## 登录

支持：

* 用户名密码
* LDAP
* OAuth2
* OIDC
* SAML

### JWT

AccessToken

RefreshToken

---

# 5.2 首页

显示：

最近会话

收藏会话

运行中的终端

资源使用情况

---

# 5.3 创建终端

用户点击：

新建终端

弹出：

Shell选择器

支持：

* bash
* zsh
* fish
* sh
* tmux

参数：

工作目录

环境变量

容器选择

主机选择

---

# 5.4 终端窗口

支持：

真实PTY

非模拟终端

---

显示能力：

UTF-8

Unicode

Emoji

ANSI Escape

256 Colors

TrueColor

Hyperlink

OSC52

Bell

Bracketed Paste

Mouse Tracking

Alternate Screen

---

# 5.5 Shell兼容性

支持：

bash

zsh

fish

nushell

xonsh

dash

tcsh

---

自动加载：

.bashrc

.zshrc

.config/fish/config.fish

---

# 5.6 ZSH主题支持

支持：

Powerlevel10k

Spaceship

Pure

Starship

Agnoster

---

支持：

Nerd Font

Ligature

Glyph

---

# 5.7 TUI兼容性

必须支持：

vim

nvim

nano

htop

btop

tmux

lazygit

k9s

ranger

yazi

mc

tig

fzf

---

兼容率要求：

99%以上

---

# 5.8 多标签页

支持：

Terminal Tabs

功能：

创建

关闭

重命名

拖拽排序

固定标签

分组标签

---

# 5.9 分屏

支持：

左右分屏

上下分屏

四宫格

动态调整比例

---

# 5.10 会话恢复

浏览器刷新：

终端不断开

网络闪断：

自动重连

恢复原会话

---

# 5.11 文件上传

拖拽上传

支持：

单文件

多文件

目录上传

---

支持：

大文件分片

断点续传

秒传

---

# 5.12 文件下载

终端右键：

Download

支持：

文件

目录

自动压缩

---

# 5.13 剪贴板

支持：

系统剪贴板

OSC52

远程复制

远程粘贴

---

# 5.14 搜索

终端历史搜索

正则搜索

大小写匹配

高亮显示

---

# 5.15 命令历史

保存：

执行命令

时间

用户

会话

主机

---

# 5.16 SSH连接

支持：

Password

Public Key

Agent Forwarding

Jump Host

ProxyCommand

---

支持导入：

~/.ssh/config

---

# 5.17 Docker终端

支持：

Container Shell

docker exec

自动发现容器

---

# 5.18 Kubernetes终端

支持：

kubectl exec

Pod Shell

Container切换

Namespace切换

---

# 5.19 共享终端

创建共享链接

权限：

只读

协作

管理员

---

支持多人同时输入

---

# 5.20 终端录制

录制：

输入

输出

窗口变化

---

格式：

asciinema

ttyrec

---

支持：

回放

倍速播放

关键帧跳转

---

# 5.21 审计

记录：

用户

IP

会话

命令

时间

结果

---

支持：

敏感命令检测

风险评分

告警

---

# 5.22 权限控制

RBAC

支持：

角色

用户组

资源组

---

# 6. 非功能需求

# 6.1 性能

输入延迟：

<20ms

输出延迟：

<50ms

---

# 6.2 并发

MVP：

1000 Session

V2：

10000 Session

---

# 6.3 可用性

99.95%

---

# 6.4 安全性

TLS1.3

JWT

CSRF

XSS

CSP

Audit

MFA

---

# 7. 后端架构

API Gateway

↓

Auth Service

↓

Terminal Service

↓

Session Service

↓

Audit Service

↓

Storage Service

↓

Runtime Service

---

# 8. 数据模型

User

Role

Session

Terminal

CommandLog

Replay

Host

Container

KubernetesCluster

AuditEvent

---

# 9. 部署架构

Nginx

↓

FastAPI

↓

Redis

↓

PostgreSQL

↓

Docker Runtime

↓

Linux Host

---

# 10. MVP范围

必须实现：

用户登录

创建终端

WebSocket通信

PTY

bash

zsh

tmux

vim

文件上传

文件下载

会话恢复

审计日志

多标签页

---

# 11. V2规划

终端共享

终端录制

SSH资产管理

Docker终端

Kubernetes终端

AI辅助分析

---

# 12. V3规划

多人协同终端

终端市场

云开发环境

在线IDE集成

Git工作区管理

DevContainer支持
