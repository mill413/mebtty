# Plugin System

MebTTY plugins are `.mtpx` packages. A package is a zip archive with a required `mebtty.plugin.json` manifest at the archive root and optional frontend assets beside it.

The current plugin runtime is frontend-focused. It supports UI panels, toolbar items, settings sections, themes, icon packs, and file providers. Backend plugin code is intentionally disabled by default.

## Package Layout

```text
my-plugin.mtpx
├── mebtty.plugin.json
└── frontend/
    └── index.js
```

`mebtty.plugin.json` must be at the root of the zip archive. Directory traversal entries, absolute paths, excessive file counts, and packages whose expanded size exceeds `MEBTTY_PLUGIN_MAX_SIZE` are rejected before installation.

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

### Manifest Rules

- `id` must contain only lowercase letters, numbers, dots, underscores, and hyphens.
- Third-party plugins cannot use the `builtin.*` namespace.
- `version` must be SemVer-like, for example `1.2.3` or `1.2.3-beta.1`.
- `schema` must be `https://mebtty.dev/schemas/plugin.v1.json`.
- `type` must be one of `theme`, `icon-pack`, `file-provider`, `panel`, or `integration`.
- `permissions` must use known permission names.

Known permissions:

| Permission | Meaning |
| ---------- | ------- |
| `ui.panel` | Contributes a terminal sidebar panel |
| `ui.toolbar` | Contributes a terminal toolbar item |
| `ui.settings` | Contributes a settings section |
| `theme.provide` | Contributes a selectable theme |
| `icons.provide` | Contributes a selectable icon pack |
| `filesystem.read` | Reads file-like data through a provider or MebTTY API |
| `filesystem.write` | Writes file-like data |
| `filesystem.delete` | Deletes file-like data |
| `filesystem.upload` | Uploads file-like data |
| `filesystem.download` | Downloads file-like data |
| `network.client` | Uses the authenticated frontend API client or browser network APIs |
| `terminal.read` | Reads terminal/session state exposed by the frontend |
| `terminal.write` | Writes terminal/session state exposed by the frontend |

## Frontend Entry

The frontend entry is loaded only when the plugin is enabled. It must export an `activate(ctx)` function, a default function, or a default object with `activate`.

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

## Runtime Context

`activate(ctx)` receives:

| Field | Description |
| ----- | ----------- |
| `ctx.plugin` | Plugin metadata returned by the backend |
| `ctx.api` | Authenticated Axios client used by the MebTTY frontend |
| `ctx.vue.h` | Vue `h` helper |
| `ctx.vue.ref` | Vue `ref` helper |
| `ctx.vue.shallowRef` | Vue `shallowRef` helper |
| `ctx.vue.computed` | Vue `computed` helper |
| `ctx.panels.register(panel)` | Register a terminal sidebar panel |
| `ctx.toolbar.register(item)` | Register a terminal toolbar item |
| `ctx.settings.registerSection(section)` | Register a settings section under the Plugins category |
| `ctx.themes.register(theme)` | Register a custom theme |
| `ctx.icons.registerPack(iconPack)` | Register a file icon pack |
| `ctx.files.registerProvider(provider)` | Register a file provider |

Plugin code runs in the browser with the current user's authentication context. Treat installed plugins as trusted code.

## File Providers

A file provider lets the file browser show non-local or virtual file trees.

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

Supported provider methods are `browse`, `read`, `write`, `upload`, `downloadUrl`, `mkdir`, `rename`, and `delete`. The UI shows actions based on the provider's capabilities and implemented methods.

## Themes

Themes must provide both dark and light token sets.

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

## Icon Packs

Icon packs map filenames, extensions, and folders to assets served from the plugin package.

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

## Build a Package

From the plugin directory:

```bash
zip -qr my-plugin.mtpx mebtty.plugin.json frontend icons
```

Then install it from Settings -> Plugins or through the API:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  -F "file=@my-plugin.mtpx" \
  http://localhost:18888/api/plugins/install
```

Install, enable, disable, delete, and update operations require an administrator account.

## Built-In Plugins

MebTTY currently ships these built-in plugins:

| ID | Purpose |
| -- | ------- |
| `builtin.file-browser` | Local file browser, preview, and editor |
| `builtin.catppuccin-theme` | Default dark/light theme tokens |
| `builtin.catppuccin-icons` | Bundled Catppuccin file icon pack |

Built-in plugins are bundled with MebTTY, cannot be deleted, cannot be installed separately, and update only when MebTTY itself is updated.

## Security Notes

- Third-party frontend plugin code runs in the browser and receives the authenticated API client.
- Install plugins only from sources you trust.
- Backend plugin code is not enabled in the current runtime.
- Plugin package signatures are reserved for a future implementation and are not enforced when `MEBTTY_PLUGIN_SIGNATURE_REQUIRED=false`.
