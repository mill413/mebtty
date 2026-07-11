# 发布流程

[English](release.md) | **简体中文**

本项目将可发布代码保留在 `master`，日常开发工作放在 `develop`。

## 分支模型

| 分支 | 用途 |
| ---- | ---- |
| `develop` | 日常开发和集成分支 |
| `master` | 发布分支；从这里打 tag |
| `feature/*` | 从 `develop` 分出的短期功能分支 |
| `fix/*` | 从 `develop` 分出的短期修复分支；除非是修复已发布版本 |

常规流程：

```bash
git switch develop
git switch -c feature/my-change

# 提交改动

git switch develop
git merge --no-ff feature/my-change
```

发布流程：

```bash
git switch develop
git pull --ff-only

# 本地验证
python -m compileall backend/app
(cd frontend && npm run build)

git switch master
git pull --ff-only
git merge --no-ff develop
git tag vX.Y.Z
git push origin master vX.Y.Z
```

GitHub Actions 发布 workflow 会校验 tag 是否可以从 `origin/master` 访问到。

## 版本 Tag

允许的 tag 格式：

- `vX.Y.Z`：稳定版本，例如 `v0.2.2`
- `vX.Y.Z.dev`：开发预发布版本，例如 `v0.3.0.dev`

稳定 tag 会创建普通 GitHub Release。`.dev` tag 会创建 prerelease，并跳过 AUR 发布。

## 本地校验 Workflow

推送 workflow 改动前运行：

```bash
./scripts/check-github-actions.sh
```

脚本会优先运行本机安装的 `actionlint`，未安装时使用其官方 Docker 镜像。它会检查 workflow 语法、表达式、Action 参数、内嵌 Shell 脚本及常见安全问题。

如需使用 `act` 额外检查本地执行计划，可运行：

```bash
./scripts/check-github-actions.sh --dry-run
```

Dry-run 会检查 job 和 step 的解析结果，但不会执行发布命令；该模式需要安装 `act`。安装仓库中的 `scripts/git-hooks/pre-push` 后，推送时会自动执行快速静态检查。

## Release Workflow 产物

推送 tag 后，`.github/workflows/release.yml` 会构建：

| 产物 | 说明 |
| ---- | ---- |
| `mebtty-X.Y.Z-linux-amd64` | Linux amd64 独立可执行文件 |
| `mebtty_X.Y.Z_amd64.deb` | Debian/Ubuntu amd64 软件包 |
| `mebtty-X.Y.Z-1.src.tar.gz` | AUR source package |

Release notes 会通过 GitHub release-notes API 和 `.github/release.yml` 生成，然后追加安装说明和产物说明。

## AUR 发布

当仓库 secret `AUR_SSH_PRIVATE_KEY` 已配置时，release workflow 可以发布 `mebtty` AUR 包。

该私钥必须能访问：

```text
ssh://aur@aur.archlinux.org/mebtty.git
```

Workflow 会：

1. 复制 `pkg/aur/PKGBUILD`、`mebtty.install` 和 `mebtty.tmpfiles`。
2. 根据当前 tag 重写 `pkgver` 和 source checksums。
3. 在 Arch Linux 容器中生成 `.SRCINFO`。
4. 将 AUR source archive 上传到 GitHub Release。
5. 当 `AUR_SSH_PRIVATE_KEY` 存在且是稳定版本时，推送更新后的 AUR 仓库。

AUR commit 使用：

```text
haruto <mill413@outlook.com>
```

## 本地包检查

### AUR

```bash
./pkg/aur/test-aur-package.sh
```

本脚本会在本机有 `makepkg` 时直接构建 AUR 包，否则通过 Arch Linux Docker 容器构建。

### Debian

```bash
./pkg/deb/build-deb.sh 0.2.2
```

Debian helper 会基于现有独立二进制构建本地 `.deb` 包；如果二进制不存在，则调用 `build.sh`。

## 安装后的运行配置

打包安装使用：

| 路径 | 用途 |
| ---- | ---- |
| `/etc/mebtty/mebtty.env` | 环境变量配置 |
| `/var/lib/mebtty/mebtty.db` | SQLite 数据库 |
| `/var/lib/mebtty/uploads` | 上传文件和头像 |
| `/var/lib/mebtty/plugins` | 已安装的第三方插件 |

修改 `/etc/mebtty/mebtty.env` 后需要重启服务：

```bash
sudo systemctl restart mebtty
```

## 发布前检查清单

- `python -m compileall backend/app`
- `cd frontend && npm run build`
- 使用 `./deploy.sh --local-test` 做本地浏览器冒烟测试
- 修改 systemd/PAM 行为时，验证本地用户认证和终端创建
- 修改插件系统行为时，验证插件安装、更新、启用、禁用和删除
- 确认 `README.md`、`README.zh-CN.md`、包文档和 release notes 与实际行为一致
