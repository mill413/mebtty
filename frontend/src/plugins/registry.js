import { computed, h, reactive, ref, shallowRef } from 'vue'
import api from '../services/api'

const state = reactive({
  plugins: [],
  panels: [],
  toolbarItems: [],
  settingsSections: [],
  themes: [],
  iconPacks: [],
  fileProviders: [],
  errors: {},
  loaded: false,
  loading: false
})

let loadGeneration = 0
let contributionSequence = 0

const localFileProvider = {
  id: 'builtin.local-files',
  label: 'Local Files',
  capabilities: ['browse', 'read', 'write', 'upload', 'download', 'mkdir', 'rename', 'delete'],
  async browse({ path = '', showHidden = false }) {
    const { data } = await api.get('/api/files/browse', {
      params: { path, show_hidden: showHidden }
    })
    return data
  },
  async read({ path }) {
    const { data } = await api.get('/api/files/read', { params: { path } })
    return data
  },
  async write({ path, content, mtime }) {
    const { data } = await api.put('/api/files/write', { path, content, mtime })
    return data
  },
  async upload({ targetDir, file }) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('target_dir', targetDir)
    const { data } = await api.post('/api/files/upload-browse', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return data
  },
  async mkdir({ path, name }) {
    const formData = new FormData()
    formData.append('path', path)
    formData.append('name', name)
    const { data } = await api.post('/api/files/mkdir', formData)
    return data
  },
  async rename({ path, newName }) {
    const formData = new FormData()
    formData.append('path', path)
    formData.append('new_name', newName)
    const { data } = await api.post('/api/files/rename', formData)
    return data
  },
  async delete({ path }) {
    const formData = new FormData()
    formData.append('path', path)
    const { data } = await api.post('/api/files/delete', formData)
    return data
  },
  downloadUrl({ path, token }) {
    return `/api/files/download-browse?path=${encodeURIComponent(path)}&token=${token}`
  }
}

function clearContributions() {
  state.plugins = []
  state.panels = []
  state.toolbarItems = []
  state.settingsSections = []
  state.themes = []
  state.iconPacks = []
  state.fileProviders = []
  state.errors = {}
}

function contributionKey(plugin, contribution, type) {
  return `${plugin.id}:${type}:${contribution.id || contribution.name || contribution.title || ++contributionSequence}`
}

function normalizeContribution(plugin, contribution, type) {
  const normalized = {
    ...contribution,
    key: contribution.key || contributionKey(plugin, contribution, type),
    pluginId: plugin.id,
    pluginName: plugin.name,
    pluginVersion: plugin.version
  }

  if (type === 'fileProvider' && normalized.id === localFileProvider.id) {
    return { ...localFileProvider, ...normalized }
  }

  return normalized
}

function appendContribution(collection, plugin, contribution, type) {
  if (!contribution || typeof contribution !== 'object') return null
  const normalized = normalizeContribution(plugin, contribution, type)
  const existingIndex = collection.findIndex((item) => {
    return item.pluginId === plugin.id && item.id && normalized.id && item.id === normalized.id
  })
  if (existingIndex >= 0) {
    collection.splice(existingIndex, 1, normalized)
  } else {
    collection.push(normalized)
  }
  return normalized
}

function appendContributionList(collection, plugin, contributions, type) {
  if (!Array.isArray(contributions)) return
  contributions.forEach((contribution) => appendContribution(collection, plugin, contribution, type))
}

function registerManifestContributions(plugin) {
  const contributes = plugin.manifest?.contributes || {}
  appendContributionList(state.panels, plugin, contributes.panels, 'panel')
  appendContributionList(state.toolbarItems, plugin, contributes.toolbarItems, 'toolbar')
  appendContributionList(state.settingsSections, plugin, contributes.settingsSections, 'settings')
  appendContributionList(state.themes, plugin, contributes.themes, 'theme')
  appendContributionList(state.iconPacks, plugin, contributes.iconPacks, 'iconPack')
  appendContributionList(state.fileProviders, plugin, contributes.fileProviders, 'fileProvider')
}

function createPluginContext(plugin) {
  return {
    plugin,
    vue: {
      h,
      ref,
      shallowRef,
      computed
    },
    panels: {
      register(panel) {
        return appendContribution(state.panels, plugin, panel, 'panel')
      }
    },
    toolbar: {
      register(item) {
        return appendContribution(state.toolbarItems, plugin, item, 'toolbar')
      }
    },
    settings: {
      registerSection(section) {
        return appendContribution(state.settingsSections, plugin, section, 'settings')
      }
    },
    themes: {
      register(theme) {
        return appendContribution(state.themes, plugin, theme, 'theme')
      }
    },
    icons: {
      registerPack(iconPack) {
        return appendContribution(state.iconPacks, plugin, iconPack, 'iconPack')
      }
    },
    files: {
      registerProvider(provider) {
        return appendContribution(state.fileProviders, plugin, provider, 'fileProvider')
      }
    }
  }
}

function normalizeAssetPath(path) {
  return String(path || '').replace(/^\/+/, '')
}

async function loadFrontendEntry(plugin) {
  const frontendEntry = normalizeAssetPath(plugin.manifest?.entry?.frontend)
  if (!frontendEntry || frontendEntry === 'builtin') return

  const url = `/api/plugins/${encodeURIComponent(plugin.id)}/assets/${frontendEntry}?v=${encodeURIComponent(plugin.version)}`
  const module = await import(/* @vite-ignore */ url)
  const activate = module.activate || module.default?.activate || module.default
  if (typeof activate === 'function') {
    await activate(createPluginContext(plugin))
  }
}

export function usePluginRuntime() {
  async function loadPlugins() {
    const generation = ++loadGeneration
    state.loading = true
    clearContributions()

    try {
      const { data } = await api.get('/api/plugins')
      if (generation !== loadGeneration) return

      const enabledPlugins = data.filter((plugin) => plugin.status === 'enabled')
      state.plugins = enabledPlugins
      enabledPlugins.forEach(registerManifestContributions)

      for (const plugin of enabledPlugins) {
        try {
          await loadFrontendEntry(plugin)
        } catch (err) {
          state.errors[plugin.id] = err.message || 'Plugin failed to load'
          console.error(`Failed to load plugin ${plugin.id}:`, err)
        }
      }

      state.loaded = true
    } finally {
      if (generation === loadGeneration) {
        state.loading = false
      }
    }
  }

  return {
    state,
    loadPlugins,
    reloadPlugins: loadPlugins,
    panels: computed(() => state.panels),
    toolbarItems: computed(() => state.toolbarItems),
    settingsSections: computed(() => state.settingsSections),
    themes: computed(() => state.themes),
    iconPacks: computed(() => state.iconPacks),
    fileProviders: computed(() => state.fileProviders)
  }
}
