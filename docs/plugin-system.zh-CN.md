# 插件系统

[English](plugin-system.md) | **简体中文**

MebTTY 插件是 `.mtpx` 包。插件包本质上是一个 zip 压缩包，根目录必须包含 `mebtty.plugin.json` manifest，旁边可以放置可选的前端资源。

当前插件运行时以浏览器前端能力为主，支持 UI 面板、工具栏按钮、设置区块、主题、图标包和文件 provider。后端插件代码默认禁用。

## 包结构

```text
my-plugin.mtpx
├── mebtty.plugin.json
└── frontend/
    └── index.js
```

`mebtty.plugin.json` 必须位于 zip 根目录。安装前会拒绝目录遍历路径、绝对路径、反斜杠分隔路径、过多文件数量，以及解压后大小超过 `MEBTTY_PLUGIN_MAX_SIZE` 的插件包。manifest 中的 entry 路径（例如 `entry.frontend`）也必须是插件包内的安全相对路径。

## Manifest

```json
{
  "schema": "https://mebtty.dev/schemas/plugin.v1.json",
  "id": "example.git-tools",
  "name": "Git Tools",
  "version": "0.1.0",
  "description": "Inspect a local Git repository.",
  "author": "Example",
  "license": "MIT",
  "mebtty": ">=0.2.0",
  "type": "integration",
  "entry": {
    "frontend": "frontend/index.js"
  },
  "permissions": [
    "ui.panel",
    "ui.toolbar",
    "ui.settings",
    "filesystem.read",
    "network.client"
  ],
  "contributes": {
    "panels": [
      {
        "id": "git-inspector",
        "title": "Git Inspector",
        "slot": "terminal.sidebar"
      }
    ],
    "toolbarItems": [
      {
        "id": "git-inspector-button",
        "title": "Git Inspector",
        "slot": "terminal.toolbar",
        "icon": "G",
        "panelId": "git-inspector"
      }
    ],
    "settingsSections": [
      {
        "id": "git-tools-settings",
        "title": "Git Tools",
        "description": "Configure the Git Tools plugin."
      }
    ]
  }
}
```

### Manifest 规则

- `id` 只能包含小写字母、数字、点、下划线和连字符。
- 第三方插件不能使用 `builtin.*` 命名空间。
- `version` 必须类似 SemVer，例如 `1.2.3` 或 `1.2.3-beta.1`。
- `schema` 必须是 `https://mebtty.dev/schemas/plugin.v1.json`。
- `type` 必须是 `theme`、`icon-pack`、`file-provider`、`panel` 或 `integration`。
- `permissions` 必须使用已知权限名。

已知权限：

| 权限 | 含义 |
| ---- | ---- |
| `ui.panel` | 贡献终端侧边栏面板 |
| `ui.toolbar` | 贡献终端工具栏按钮 |
| `ui.settings` | 贡献设置区块 |
| `theme.provide` | 贡献可选择主题 |
| `icons.provide` | 贡献可选择图标包 |
| `filesystem.read` | 通过 provider 或 MebTTY API 读取文件类数据 |
| `filesystem.write` | 写入文件类数据 |
| `filesystem.delete` | 删除文件类数据 |
| `filesystem.upload` | 上传文件类数据 |
| `filesystem.download` | 下载文件类数据 |
| `network.client` | 使用带认证的前端 API client 或浏览器网络 API |
| `terminal.read` | 读取前端暴露的终端/会话状态 |
| `terminal.write` | 写入前端暴露的终端/会话状态 |

## 前端入口

前端入口只会在插件启用后加载。入口模块必须导出 `activate(ctx)` 函数、默认函数，或带 `activate` 的默认对象。

```js
export function activate(ctx) {
  const { h } = ctx.vue

  ctx.panels.register({
    id: 'hello-panel',
    title: 'Hello',
    slot: 'terminal.sidebar',
    component: {
      name: 'HelloPanel',
      setup() {
        return () => h('div', { style: 'padding: 12px' }, 'Hello from a plugin')
      }
    }
  })

  ctx.toolbar.register({
    id: 'hello-button',
    title: 'Hello',
    icon: 'H',
    slot: 'terminal.toolbar',
    panelId: 'hello-panel'
  })
}
```

## 运行时上下文

`activate(ctx)` 会收到：

| 字段 | 说明 |
| ---- | ---- |
| `ctx.plugin` | 后端返回的插件元数据 |
| `ctx.api` | MebTTY 前端使用的带认证 Axios client |
| `ctx.vue.h` | Vue `h` helper |
| `ctx.vue.ref` | Vue `ref` helper |
| `ctx.vue.shallowRef` | Vue `shallowRef` helper |
| `ctx.vue.computed` | Vue `computed` helper |
| `ctx.panels.register(panel)` | 注册终端侧边栏面板 |
| `ctx.toolbar.register(item)` | 注册终端工具栏按钮 |
| `ctx.settings.registerSection(section)` | 在“插件”分类下注册设置区块 |
| `ctx.themes.register(theme)` | 注册自定义主题 |
| `ctx.icons.registerPack(iconPack)` | 注册文件图标包 |
| `ctx.files.registerProvider(provider)` | 注册文件 provider |

插件代码运行在浏览器里，并带有当前用户的认证上下文。应把已安装插件视为可信代码。

## 文件 Provider

文件 provider 可以让文件浏览器展示非本地或虚拟文件树。

```js
ctx.files.registerProvider({
  id: 'example-readonly',
  label: 'Example Files',
  scheme: 'example',
  capabilities: ['browse', 'read'],
  async browse({ path }) {
    return {
      path: path || 'example://root',
      absolute_path: path || 'example://root',
      parent: null,
      items: [
        {
          name: 'README.md',
          path: 'example://root/README.md',
          is_dir: false,
          size: 14,
          mime: 'text/markdown',
          is_text: true,
          modified: new Date().toISOString(),
          permissions: '444',
          accessible: true
        }
      ]
    }
  },
  async read({ path }) {
    return {
      name: path.split('/').pop(),
      path,
      mime: 'text/markdown',
      size: 14,
      mtime: Date.now() / 1000,
      modified: new Date().toISOString(),
      encoding: 'utf-8',
      is_text: true,
      content: '# Hello\n'
    }
  }
})
```

支持的 provider 方法包括 `browse`、`read`、`write`、`upload`、`downloadUrl`、`mkdir`、`rename` 和 `delete`。UI 会根据 provider 的 capabilities 和实际实现的方法显示可用操作。

## 主题

主题必须同时提供深色和浅色 token。

```js
ctx.themes.register({
  id: 'example-green',
  label: 'Example Green',
  modes: {
    dark: {
      bg: '#101815',
      bgDeep: '#0b120f',
      surface: '#17231f',
      surfaceHover: '#20342c',
      overlay: '#294339',
      text: '#d8f3e7',
      subtext: '#9ac8b5',
      border: '#35594b',
      accent: '#10b981'
    },
    light: {
      bg: '#f4fbf8',
      bgDeep: '#e9f5ef',
      surface: '#dcefe6',
      surfaceHover: '#cae5d8',
      overlay: '#b3d6c5',
      text: '#17352a',
      subtext: '#4d7666',
      border: '#98c7b4',
      accent: '#059669'
    }
  }
})
```

## 图标包

图标包将文件名、扩展名和文件夹名映射到插件包中提供的资源。

```js
ctx.icons.registerPack({
  id: 'example-icons',
  label: 'Example Icons',
  assetsBase: `/api/plugins/${encodeURIComponent(ctx.plugin.id)}/assets/icons`,
  fallbackFile: 'file.svg',
  fallbackFolder: 'folder.svg',
  extensions: {
    '.md': 'markdown.svg'
  },
  files: {
    'README.md': 'readme.svg'
  },
  folders: {
    src: 'folder-source.svg'
  }
})
```

## 构建插件包

在插件目录中执行：

```bash
zip -qr my-plugin.mtpx mebtty.plugin.json frontend icons
```

然后从“设置 -> 插件”安装，或通过 API 安装：

```bash
curl -H "Authorization: Bearer $TOKEN" \
  -F "file=@my-plugin.mtpx" \
  http://localhost:18888/api/plugins/install
```

安装、启用、禁用、删除和更新插件都需要管理员账户。

## 内置插件

MebTTY 当前内置这些插件：

| ID | 用途 |
| -- | ---- |
| `builtin.file-browser` | 本地文件浏览、预览和编辑 |
| `builtin.catppuccin-theme` | 默认深色/浅色主题 token |
| `builtin.catppuccin-icons` | 随仓库分发的 Catppuccin 文件图标包 |

内置插件随 MebTTY 一起打包，不能删除，不能单独安装，更新也只跟随 MebTTY 版本。

## 安全说明

- 第三方前端插件代码运行在浏览器中，并可获得带认证的 API client。
- 只安装来自可信来源的插件。
- 当前运行时不启用后端插件代码。
- 插件包签名是预留能力；当 `MEBTTY_PLUGIN_SIGNATURE_REQUIRED=false` 时不会强制校验签名。
