# Debian 包打包

本目录包含构建 MebTTY Debian 软件包所需的元数据和脚本。

## 目录结构

```
pkg/deb/
└── DEBIAN/
    ├── control      # 包描述信息（版本由 CI 动态注入）
    ├── postinst     # 安装后执行的脚本
    ├── postrm       # 卸载后执行的脚本
    └── prerm        # 卸载前执行的脚本
```

## 文件说明

### `DEBIAN/control`

定义软件包的基本信息，包括：
- 包名、版本（CI 自动替换 `${VERSION}`）
- 架构：amd64
- 依赖：`libc6 (>= 2.36)`
- 描述和主页链接

### `DEBIAN/postinst`

安装完成后自动执行：
- 创建数据目录 `/var/lib/mebtty/uploads` 和 `/var/lib/mebtty/plugins`
- 生成随机密钥并写入 `/etc/mebtty/mebtty.env`（如不存在）
- 向已有环境变量文件补充带注释的可选配置项
- 启用并启动 systemd 服务

### `DEBIAN/prerm`

卸载前自动执行：
- 停止并禁用 systemd 服务

### `DEBIAN/postrm`

卸载后自动执行：
- `purge` 时删除数据目录和配置文件
- 重新加载 systemd 配置

## 构建流程

GitHub Actions 会自动执行以下步骤：

1. 构建前端（`npm run build`）
2. 使用 PyInstaller 打包后端为单一可执行文件
3. 创建临时目录结构：
   ```
   mebtty_VERSION_amd64/
   ├── DEBIAN/              # 从 pkg/deb/DEBIAN/ 复制
   ├── usr/local/bin/       # mebtty 可执行文件
   └── lib/systemd/system/  # mebtty.service
   ```
4. 执行 `dpkg-deb --build` 生成 `.deb` 包
5. 上传到 GitHub Release

## 本地构建

使用 `build-deb.sh` 脚本一键打包：

```bash
# 构建指定版本
./pkg/deb/build-deb.sh 1.0.0

# 使用 git tag 版本（如果当前有 tag）
./pkg/deb/build-deb.sh

# 清理构建产物
./pkg/deb/build-deb.sh --clean
```

脚本会自动：
1. 检查依赖（dpkg-deb）
2. 如果可执行文件不存在，先调用 `build.sh` 构建
3. 创建包目录结构并复制所有文件
4. 执行 `dpkg-deb --build` 生成 `.deb` 包
5. 输出安装和卸载命令

## 安装和卸载

```bash
# 安装（自动启用服务）
sudo dpkg -i mebtty_1.0.0_amd64.deb

# 查看服务状态
sudo systemctl status mebtty

# 卸载（保留数据和配置）
sudo dpkg -r mebtty

# 完全清除（删除数据和配置）
sudo dpkg -P mebtty
```

常用路径：

| 路径 | 用途 |
| ---- | ---- |
| `/usr/local/bin/mebtty` | 已安装的可执行文件 |
| `/etc/mebtty/mebtty.env` | 环境变量配置文件 |
| `/var/lib/mebtty/mebtty.db` | SQLite 数据库 |
| `/var/lib/mebtty/uploads` | 上传文件与头像 |
| `/var/lib/mebtty/plugins` | 已安装的第三方插件 |

修改 `/etc/mebtty/mebtty.env` 后需要重启服务：

```bash
sudo systemctl restart mebtty
```

插件相关配置项包括：

```bash
# MEBTTY_PLUGIN_DIR=/var/lib/mebtty/plugins
# MEBTTY_PLUGIN_MAX_SIZE=20971520
# MEBTTY_PLUGIN_INSTALL_ENABLED=true
# MEBTTY_PLUGIN_SIGNATURE_REQUIRED=false
# MEBTTY_PLUGIN_BACKEND_CODE_ENABLED=false
```

## 相关文件

- `.github/workflows/release.yml` — CI 发布流程
- `mebtty.service` — systemd 服务定义（打包时复制到 `/lib/systemd/system/`）
- `build.sh` — 构建可执行文件的脚本
- `docs/release.md` — 分支、发布、tag 和 AUR 流程说明
