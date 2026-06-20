<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { CUSTOM_THEME_FIELDS, CUSTOM_THEME_MODES, DEFAULT_CUSTOM_THEME, useSettingsStore } from '../stores/settings'
import { useThemeStore } from '../stores/theme'
import { useAuthStore } from '../stores/auth'
import { setLocale, resetToBrowserLocale, getSupportedLocales, hasUserLocale } from '../i18n'
import api from '../services/api'
import { usePluginRuntime } from '../plugins/registry'
import PluginSettingsSectionHost from '../components/plugins/PluginSettingsSectionHost.vue'

const props = defineProps({
  embedded: { type: Boolean, default: false }
})

const { t, locale: i18nLocale } = useI18n()
const router = useRouter()
const settingsStore = useSettingsStore()
const themeStore = useThemeStore()
const authStore = useAuthStore()
const pluginRuntime = usePluginRuntime()

const locales = getSupportedLocales()
const localeLabels = { 'en-US': 'English', 'zh-CN': '简体中文', 'zh-TW': '繁體中文', 'ja': '日本語' }
const isAutoLocale = ref(!hasUserLocale())
const currentLocale = computed(() => isAutoLocale.value ? 'auto' : i18nLocale.value)

function changeLanguage(locale) {
  if (locale === 'auto') {
    isAutoLocale.value = true
    resetToBrowserLocale()
  } else {
    isAutoLocale.value = false
    setLocale(locale)
  }
}

const accentPresets = ['#7c3aed', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#06b6d4']
const customThemeFields = CUSTOM_THEME_FIELDS
const customThemeModes = CUSTOM_THEME_MODES
const tabFormat = ref('')
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordError = ref('')
const passwordSuccess = ref(false)
const plugins = ref([])
const pluginsLoading = ref(false)
const pluginsError = ref('')
const pluginsMessage = ref('')
const pluginInstalling = ref(false)
const pluginSettingsSections = computed(() => pluginRuntime.settingsSections.value)
const pluginThemes = computed(() => pluginRuntime.themes.value.filter((theme) => theme?.id && theme?.modes?.dark && theme?.modes?.light))
const pluginIconPacks = computed(() => pluginRuntime.iconPacks.value.filter((pack) => pack?.id && pack?.assetsBase))
const selectedPluginThemeId = computed(() => settingsStore.pluginSettings.activeThemeId || '')
const selectedIconPackId = computed(() => settingsStore.pluginSettings.activeIconPackId || pluginIconPacks.value[0]?.id || '')
const activeSection = ref('appearance')
const sectionRefs = ref({})
const activeThemeAccent = computed(() => {
  if (!settingsStore.customThemeEnabled) return settingsStore.accentColor
  const mode = themeStore.resolved === 'light' ? 'light' : 'dark'
  return settingsStore.customTheme[mode]?.accent || settingsStore.accentColor
})

const settingSections = [
  { key: 'appearance', label: 'settings.sectionAppearance' },
  { key: 'terminal', label: 'settings.sectionTerminal' },
  { key: 'files', label: 'settings.sectionFiles' },
  { key: 'status', label: 'settings.sectionStatus' },
  { key: 'plugins', label: 'settings.sectionPlugins' },
  { key: 'account', label: 'settings.sectionAccount' }
]

function setSectionRef(key, el) {
  if (el) sectionRefs.value[key] = el
}

function scrollToSection(key) {
  activeSection.value = key
  sectionRefs.value[key]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// Drag and drop for status bar items
const dragIndex = ref(null)
const dragOverIndex = ref(null)

function onDragStart(index, event) {
  dragIndex.value = index
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', index.toString())
}

function onDragOver(index, event) {
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
  dragOverIndex.value = index
}

function onDragLeave() {
  dragOverIndex.value = null
}

function onDrop(index, event) {
  event.preventDefault()
  if (dragIndex.value !== null && dragIndex.value !== index) {
    settingsStore.reorderStatusBarItems(dragIndex.value, index)
  }
  dragOverIndex.value = null
}

function onDragEnd() {
  dragIndex.value = null
  dragOverIndex.value = null
}

onMounted(async () => {
  if (!authStore.user) await authStore.fetchUser()
  if (!settingsStore.loaded) await settingsStore.fetchSettings()
  tabFormat.value = settingsStore.tabTitleFormat
  await refreshPlugins()
})

function changeTheme(mode) {
  themeStore.setMode(mode)
  settingsStore.themeMode = mode
  settingsStore.applyThemeColors()
  settingsStore.updateSettings({ theme_mode: mode })
}

function previewAccentColor(color) {
  settingsStore.previewAccentColor(color)
}

function saveAccentColor(color) {
  settingsStore.saveAccentColor(color)
}

function selectAccentColor(color) {
  previewAccentColor(color)
  saveAccentColor(color)
}

function onCustomColorInput(e) {
  previewAccentColor(e.target.value)
}

function onCustomColorChange(e) {
  saveAccentColor(e.target.value)
}

function toggleCustomTheme(enabled) {
  settingsStore.toggleCustomTheme(enabled)
}

function previewCustomThemeColor(mode, key, color) {
  settingsStore.previewCustomThemeColor(mode, key, color)
}

function saveCustomThemeColor(mode, key, color) {
  settingsStore.saveCustomThemeColor(mode, key, color)
}

function resetCustomTheme() {
  settingsStore.resetCustomTheme()
}

function normalizePluginTheme(theme) {
  return {
    dark: { ...DEFAULT_CUSTOM_THEME.dark, ...theme.modes.dark },
    light: { ...DEFAULT_CUSTOM_THEME.light, ...theme.modes.light }
  }
}

function selectPluginTheme(themeId) {
  if (!themeId) {
    const { activeThemeId, ...rest } = settingsStore.pluginSettings
    settingsStore.updatePluginSettings(rest)
    return
  }

  const theme = pluginThemes.value.find((candidate) => candidate.id === themeId)
  if (!theme) return
  const nextTheme = normalizePluginTheme(theme)
  settingsStore.customThemeEnabled = true
  settingsStore.customTheme = nextTheme
  settingsStore.applyThemeColors()
  settingsStore.updatePluginSettings({ ...settingsStore.pluginSettings, activeThemeId: themeId })
  settingsStore.updateSettings({
    custom_theme_enabled: true,
    custom_theme: JSON.stringify(nextTheme)
  })
}

function selectIconPack(iconPackId) {
  settingsStore.updatePluginSettings({
    ...settingsStore.pluginSettings,
    activeIconPackId: iconPackId
  })
}

function saveTabFormat() {
  if (tabFormat.value.trim()) {
    settingsStore.updateSettings({ tab_title_format: tabFormat.value })
  }
}

async function uploadAvatar(e) {
  const file = e.target.files[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  try {
    await api.post('/api/auth/avatar', formData)
    await authStore.fetchUser()
  } catch (err) {
    console.error('Failed to upload avatar:', err)
  }
}

function getAvatarUrl() {
  if (authStore.user?.avatar) {
    return `/api/auth/avatar/${authStore.user.avatar}`
  }
  return null
}

function getInitials() {
  const name = authStore.username || 'U'
  return name.charAt(0).toUpperCase()
}

async function changePassword() {
  passwordError.value = ''
  passwordSuccess.value = false

  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = t('settings.passwordMismatch')
    return
  }
  if (newPassword.value.length < 4) {
    passwordError.value = t('settings.passwordTooShort')
    return
  }

  try {
    await api.post('/api/auth/change-password', {
      old_password: oldPassword.value,
      new_password: newPassword.value
    })
    passwordSuccess.value = true
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    setTimeout(() => { passwordSuccess.value = false }, 3000)
  } catch (err) {
    passwordError.value = err.response?.data?.detail || 'Failed to change password'
  }
}

function changeSidebarPosition(pos) {
  settingsStore.updateSettings({ sidebar_position: pos })
}

let timeoutDebounce = null
function changeTimeout(value) {
  clearTimeout(timeoutDebounce)
  timeoutDebounce = setTimeout(() => {
    settingsStore.updateSettings({ session_timeout: parseInt(value) || 0 })
  }, 500)
}

const timeoutPresets = [
  { value: 0, label: 'settings.timeoutDisabled' },
  { value: 1, label: '1h' },
  { value: 6, label: '6h' },
  { value: 12, label: '12h' },
  { value: 24, label: '24h' },
  { value: 48, label: '48h' }
]

function goBack() {
  router.push('/terminal')
}

function logout() {
  authStore.logout()
  router.push('/login')
}

function setPluginNotice(message = '', error = '') {
  pluginsMessage.value = message
  pluginsError.value = error
}

async function loadPlugins() {
  pluginsLoading.value = true
  setPluginNotice()
  try {
    const { data } = await api.get('/api/plugins')
    plugins.value = data
  } catch (err) {
    setPluginNotice('', err.response?.data?.detail || t('settings.pluginLoadFailed'))
  } finally {
    pluginsLoading.value = false
  }
}

async function refreshPluginRuntime() {
  try {
    await pluginRuntime.reloadPlugins()
  } catch (err) {
    console.error('Failed to refresh plugin runtime:', err)
  }
}

async function refreshPlugins() {
  await loadPlugins()
  await refreshPluginRuntime()
}

async function installPlugin(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  pluginInstalling.value = true
  setPluginNotice()
  const formData = new FormData()
  formData.append('file', file)

  try {
    await api.post('/api/plugins/install', formData)
    setPluginNotice(t('settings.pluginInstalled'))
    await refreshPlugins()
  } catch (err) {
    setPluginNotice('', err.response?.data?.detail || t('settings.pluginInstallFailed'))
  } finally {
    pluginInstalling.value = false
  }
}

async function enablePlugin(plugin) {
  setPluginNotice()
  try {
    await api.post(`/api/plugins/${encodeURIComponent(plugin.id)}/enable`)
    setPluginNotice(t('settings.pluginEnabled'))
    await refreshPlugins()
  } catch (err) {
    setPluginNotice('', err.response?.data?.detail || t('settings.pluginActionFailed'))
  }
}

async function disablePlugin(plugin) {
  setPluginNotice()
  try {
    await api.post(`/api/plugins/${encodeURIComponent(plugin.id)}/disable`)
    setPluginNotice(t('settings.pluginDisabled'))
    await refreshPlugins()
  } catch (err) {
    setPluginNotice('', err.response?.data?.detail || t('settings.pluginActionFailed'))
  }
}

async function deletePlugin(plugin) {
  if (!window.confirm(t('settings.pluginDeleteConfirm', { name: plugin.name }))) return

  setPluginNotice()
  try {
    await api.delete(`/api/plugins/${encodeURIComponent(plugin.id)}`)
    setPluginNotice(t('settings.pluginDeleted'))
    await refreshPlugins()
  } catch (err) {
    setPluginNotice('', err.response?.data?.detail || t('settings.pluginActionFailed'))
  }
}

function canDisablePlugin(plugin) {
  return !plugin.builtin || plugin.id === 'builtin.file-browser'
}

function pluginStatusLabel(status) {
  return t(`settings.pluginStatus${status.charAt(0).toUpperCase()}${status.slice(1)}`)
}

function pluginTypeLabel(type) {
  const key = type.replace(/(^|-)([a-z])/g, (_, _sep, char) => char.toUpperCase())
  return t(`settings.pluginType${key}`)
}

function pluginPermissionLabel(permission) {
  return t(`settings.pluginPermission.${permission}`)
}
</script>

<template>
  <div class="settings-page">
    <header v-if="!embedded" class="top-bar">
      <div class="top-bar-left">
        <button class="btn-icon" @click="goBack" :title="t('settings.back')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
        </button>
        <span class="page-title">{{ t('settings.title') }}</span>
      </div>
      <div class="top-bar-right">
        <span class="username">{{ authStore.username }}</span>
        <button class="btn-icon" @click="logout" :title="t('home.logout')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
      </div>
    </header>

    <main class="settings-layout">
      <nav class="settings-sidebar" :aria-label="t('settings.categories')">
        <button
          v-for="section in settingSections"
          :key="section.key"
          class="settings-nav-item"
          :class="{ active: activeSection === section.key }"
          @click="scrollToSection(section.key)"
        >
          {{ t(section.label) }}
        </button>
      </nav>

      <section class="settings-content">
        <section class="settings-section" :ref="(el) => setSectionRef('appearance', el)">
          <div class="settings-section-head">
            <h2>{{ t('settings.sectionAppearance') }}</h2>
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.language') }}</h3>
              <p>{{ t('settings.languageDesc') }}</p>
            </div>
            <div class="setting-control">
              <select class="setting-select" :value="currentLocale" @change="changeLanguage($event.target.value)">
                <option value="auto">{{ t('settings.languageAuto') }}</option>
                <option v-for="loc in locales" :key="loc" :value="loc">{{ localeLabels[loc] || loc }}</option>
              </select>
            </div>
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.colorMode') }}</h3>
              <p>{{ t('settings.colorModeDesc') }}</p>
            </div>
            <div class="setting-control">
              <div class="theme-selector">
                <button
                  v-for="mode in ['system', 'dark', 'light']"
                  :key="mode"
                  :class="{ active: themeStore.mode === mode }"
                  @click="changeTheme(mode)"
                  :title="t(`settings.${mode}`)"
                >
                  <svg v-if="mode === 'system'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                    <line x1="8" y1="21" x2="16" y2="21" />
                    <line x1="12" y1="17" x2="12" y2="21" />
                  </svg>
                  <svg v-else-if="mode === 'dark'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
                  </svg>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="5" />
                    <line x1="12" y1="1" x2="12" y2="3" />
                    <line x1="12" y1="21" x2="12" y2="23" />
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                    <line x1="1" y1="12" x2="3" y2="12" />
                    <line x1="21" y1="12" x2="23" y2="12" />
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <div class="setting-row" v-if="pluginThemes.length">
            <div class="setting-info">
              <h3>{{ t('settings.pluginTheme') }}</h3>
              <p>{{ t('settings.pluginThemeDesc') }}</p>
            </div>
            <div class="setting-control">
              <select class="setting-select" :value="selectedPluginThemeId" @change="selectPluginTheme($event.target.value)">
                <option value="">{{ t('settings.pluginThemeCustom') }}</option>
                <option v-for="theme in pluginThemes" :key="theme.key" :value="theme.id">
                  {{ theme.label || theme.title || theme.id }}
                </option>
              </select>
            </div>
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.accentColor') }}</h3>
              <p>{{ t('settings.accentColorDesc') }}</p>
            </div>
            <div class="setting-control">
              <div class="color-presets">
                <button
                  v-for="color in accentPresets"
                  :key="color"
                  class="color-preset"
                  :class="{ active: activeThemeAccent === color }"
                  :style="{ background: color }"
                  @click="selectAccentColor(color)"
                >
                  <svg v-if="activeThemeAccent === color" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </button>
                <label class="color-custom" :title="t('settings.accentColor')">
                  <input
                    type="color"
                    :value="activeThemeAccent"
                    @input="onCustomColorInput"
                    @change="onCustomColorChange"
                  />
                  <span class="color-custom-icon">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="16" />
                      <line x1="8" y1="12" x2="16" y2="12" />
                    </svg>
                  </span>
                </label>
              </div>
            </div>
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.customTheme') }}</h3>
              <p>{{ t('settings.customThemeDesc') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input type="checkbox" :checked="settingsStore.customThemeEnabled" @change="toggleCustomTheme($event.target.checked)" />
                <span class="slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-row setting-row-column custom-theme-row" v-if="settingsStore.customThemeEnabled">
            <div class="setting-info">
              <h3>{{ t('settings.customThemeColors') }}</h3>
              <p>{{ t('settings.customThemeColorsDesc') }}</p>
            </div>
            <div class="setting-control-full">
              <div class="custom-theme-mode-list">
                <div v-for="mode in customThemeModes" :key="mode" class="custom-theme-mode">
                  <h4>{{ t(`settings.${mode}`) }}</h4>
                  <div class="custom-theme-grid">
                    <label
                      v-for="field in customThemeFields"
                      :key="`${mode}-${field.key}`"
                      class="theme-color-field"
                    >
                      <span>{{ t(field.label) }}</span>
                      <div class="theme-color-control">
                        <input
                          type="color"
                          :value="settingsStore.customTheme[mode][field.key]"
                          @input="previewCustomThemeColor(mode, field.key, $event.target.value)"
                          @change="saveCustomThemeColor(mode, field.key, $event.target.value)"
                        />
                        <code>{{ settingsStore.customTheme[mode][field.key] }}</code>
                      </div>
                    </label>
                  </div>
                </div>
              </div>
              <div class="custom-theme-actions">
                <button class="btn-secondary" @click="resetCustomTheme">
                  {{ t('settings.resetCustomTheme') }}
                </button>
              </div>
            </div>
          </div>

          <div v-if="pluginSettingsSections.length" class="setting-row setting-row-column">
            <div class="setting-info">
              <h3>{{ t('settings.pluginSettings') }}</h3>
              <p>{{ t('settings.pluginSettingsDesc') }}</p>
            </div>
            <div class="setting-control-full">
              <div class="plugin-settings-list">
                <PluginSettingsSectionHost
                  v-for="section in pluginSettingsSections"
                  :key="section.key"
                  :section="section"
                />
              </div>
            </div>
          </div>
        </section>

        <section class="settings-section" :ref="(el) => setSectionRef('terminal', el)">
          <div class="settings-section-head">
            <h2>{{ t('settings.sectionTerminal') }}</h2>
          </div>

          <div class="setting-row setting-row-column">
            <div class="setting-info">
              <h3>{{ t('settings.tabTitleFormat') }}</h3>
              <p>{{ t('settings.tabTitleFormatDesc') }}</p>
            </div>
            <div class="setting-control-full">
              <input
                v-model="tabFormat"
                type="text"
                class="setting-input"
                @blur="saveTabFormat"
                @keyup.enter="saveTabFormat"
              />
              <div class="format-preview">
                <span class="preview-label">{{ t('settings.tabTitlePreview') }}:</span>
                <span class="preview-value">{{ tabFormat.replace('{shell}', 'bash').replace('{index}', '1').replace('{title}', '').replace('{user}', 'admin').replace('{cwd}', '~/projects') }}</span>
              </div>
              <div class="format-hint">
                <code>{shell}</code> <code>{index}</code> <code>{title}</code> <code>{user}</code> <code>{cwd}</code>
              </div>
            </div>
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.sessionTimeout') }}</h3>
              <p>{{ t('settings.sessionTimeoutDesc') }}</p>
            </div>
            <div class="setting-control-full">
              <div class="timeout-controls">
                <input
                  type="number"
                  class="setting-input setting-input-number"
                  :value="settingsStore.sessionTimeout"
                  min="0"
                  step="1"
                  @input="changeTimeout($event.target.value)"
                />
                <span class="timeout-unit">{{ t('settings.hours') }}</span>
              </div>
              <div class="timeout-presets">
                <button
                  v-for="preset in timeoutPresets"
                  :key="preset.value"
                  class="timeout-preset"
                  :class="{ active: settingsStore.sessionTimeout === preset.value }"
                  @click="changeTimeout(preset.value)"
                >
                  {{ preset.value === 0 ? t(preset.label) : preset.label }}
                </button>
              </div>
            </div>
          </div>
        </section>

        <section class="settings-section" :ref="(el) => setSectionRef('files', el)">
          <div class="settings-section-head">
            <h2>{{ t('settings.sectionFiles') }}</h2>
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.sidebarPosition') }}</h3>
              <p>{{ t('settings.sidebarPositionDesc') }}</p>
            </div>
            <div class="setting-control">
              <div class="toggle-group">
                <button
                  :class="{ active: settingsStore.sidebarPosition === 'left' }"
                  @click="changeSidebarPosition('left')"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <line x1="9" y1="3" x2="9" y2="21" />
                  </svg>
                  {{ t('settings.left') }}
                </button>
                <button
                  :class="{ active: settingsStore.sidebarPosition === 'right' }"
                  @click="changeSidebarPosition('right')"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" />
                    <line x1="15" y1="3" x2="15" y2="21" />
                  </svg>
                  {{ t('settings.right') }}
                </button>
              </div>
            </div>
          </div>

          <div class="setting-row" v-if="pluginIconPacks.length">
            <div class="setting-info">
              <h3>{{ t('settings.fileIconPack') }}</h3>
              <p>{{ t('settings.fileIconPackDesc') }}</p>
            </div>
            <div class="setting-control">
              <select class="setting-select" :value="selectedIconPackId" @change="selectIconPack($event.target.value)">
                <option v-for="pack in pluginIconPacks" :key="pack.key" :value="pack.id">
                  {{ pack.label || pack.title || pack.id }}
                </option>
              </select>
            </div>
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.fileAutoSave') }}</h3>
              <p>{{ t('settings.fileAutoSaveDesc') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input type="checkbox" :checked="settingsStore.fileAutoSave" @change="settingsStore.toggleFileAutoSave($event.target.checked)" />
                <span class="slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.fileLineNumbers') }}</h3>
              <p>{{ t('settings.fileLineNumbersDesc') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input type="checkbox" :checked="settingsStore.fileShowLineNumbers" @change="settingsStore.toggleFileShowLineNumbers($event.target.checked)" />
                <span class="slider"></span>
              </label>
            </div>
          </div>
        </section>

        <section class="settings-section" :ref="(el) => setSectionRef('status', el)">
          <div class="settings-section-head">
            <h2>{{ t('settings.sectionStatus') }}</h2>
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.statusBar') }}</h3>
              <p>{{ t('settings.statusBarDesc') }}</p>
            </div>
            <div class="setting-control">
              <label class="switch">
                <input type="checkbox" :checked="settingsStore.statusBarVisible" @change="settingsStore.toggleStatusBar($event.target.checked)" />
                <span class="slider"></span>
              </label>
            </div>
          </div>

          <div class="setting-row setting-row-column" v-if="settingsStore.statusBarVisible">
            <div class="setting-info">
              <h3>{{ t('settings.statusBarItems') }}</h3>
              <p>{{ t('settings.statusBarItemsDesc') }}</p>
            </div>
            <div class="setting-control-full">
              <div class="statusbar-items-list">
                <div
                  v-for="(item, index) in settingsStore.statusBarItems"
                  :key="item.key"
                  class="statusbar-item-row"
                  :class="{ 'dragging': dragIndex === index, 'drag-over': dragOverIndex === index }"
                  draggable="true"
                  @dragstart="onDragStart(index, $event)"
                  @dragover="onDragOver(index, $event)"
                  @dragleave="onDragLeave"
                  @drop="onDrop(index, $event)"
                  @dragend="onDragEnd"
                >
                  <div class="drag-handle" :title="t('settings.dragToReorder')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                      <circle cx="9" cy="5" r="1.5"/>
                      <circle cx="15" cy="5" r="1.5"/>
                      <circle cx="9" cy="12" r="1.5"/>
                      <circle cx="15" cy="12" r="1.5"/>
                      <circle cx="9" cy="19" r="1.5"/>
                      <circle cx="15" cy="19" r="1.5"/>
                    </svg>
                  </div>
                  <label class="checkbox-label">
                    <input type="checkbox" :checked="item.visible" @change="settingsStore.toggleStatusBarItemVisible(item.key, $event.target.checked)" />
                    <span>{{ t('settings.statusItem' + item.key.charAt(0).toUpperCase() + item.key.slice(1)) }}</span>
                  </label>
                  <select class="position-select" :value="item.position" @change="settingsStore.updateStatusBarItemPosition(item.key, $event.target.value)" :disabled="!item.visible">
                    <option value="left">{{ t('settings.statusPositionLeft') }}</option>
                    <option value="right">{{ t('settings.statusPositionRight') }}</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="settings-section" :ref="(el) => setSectionRef('plugins', el)">
          <div class="settings-section-head">
            <h2>{{ t('settings.sectionPlugins') }}</h2>
          </div>

          <div class="setting-row setting-row-column">
            <div class="setting-info">
              <h3>{{ t('settings.pluginInstall') }}</h3>
              <p>{{ t('settings.pluginInstallDesc') }}</p>
            </div>
            <div class="setting-control-full">
              <div class="plugin-toolbar">
                <label class="btn-upload" :class="{ disabled: pluginInstalling }">
                  <input type="file" accept=".mtpx" @change="installPlugin" hidden :disabled="pluginInstalling" />
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  {{ pluginInstalling ? t('settings.pluginInstalling') : t('settings.pluginChoosePackage') }}
                </label>
                <button class="btn-secondary" @click="refreshPlugins" :disabled="pluginsLoading">
                  {{ pluginsLoading ? t('settings.pluginRefreshing') : t('settings.pluginRefresh') }}
                </button>
              </div>
              <p v-if="pluginsError" class="msg-error">{{ pluginsError }}</p>
              <p v-if="pluginsMessage" class="msg-success">{{ pluginsMessage }}</p>
            </div>
          </div>

          <div class="setting-row setting-row-column">
            <div class="setting-info">
              <h3>{{ t('settings.installedPlugins') }}</h3>
              <p>{{ t('settings.installedPluginsDesc') }}</p>
            </div>
            <div class="setting-control-full">
              <div v-if="pluginsLoading" class="plugin-empty">{{ t('settings.pluginLoading') }}</div>
              <div v-else-if="plugins.length === 0" class="plugin-empty">{{ t('settings.noPlugins') }}</div>
              <div v-else class="plugin-list">
                <div v-for="plugin in plugins" :key="plugin.id" class="plugin-item">
                  <div class="plugin-main">
                    <div class="plugin-title-row">
                      <h4>{{ plugin.name }}</h4>
                      <span class="plugin-badge" :class="{ builtin: plugin.builtin }">
                        {{ plugin.builtin ? t('settings.pluginBuiltin') : t('settings.pluginThirdParty') }}
                      </span>
                      <span class="plugin-status" :class="plugin.status">
                        {{ pluginStatusLabel(plugin.status) }}
                      </span>
                    </div>
                    <div class="plugin-meta">
                      <code>{{ plugin.id }}</code>
                      <span>{{ pluginTypeLabel(plugin.type) }}</span>
                      <span>v{{ plugin.version }}</span>
                    </div>
                    <p v-if="plugin.manifest.description" class="plugin-description">
                      {{ plugin.manifest.description }}
                    </p>
                    <div class="plugin-permissions" v-if="plugin.permissions.length">
                      <span v-for="permission in plugin.permissions" :key="permission" class="plugin-permission">
                        {{ pluginPermissionLabel(permission) }}
                      </span>
                    </div>
                  </div>
                  <div class="plugin-actions">
                    <button
                      v-if="plugin.status !== 'enabled'"
                      class="btn-secondary"
                      @click="enablePlugin(plugin)"
                    >
                      {{ t('settings.pluginEnable') }}
                    </button>
                    <button
                      v-else
                      class="btn-secondary"
                      @click="disablePlugin(plugin)"
                      :disabled="!canDisablePlugin(plugin)"
                    >
                      {{ t('settings.pluginDisable') }}
                    </button>
                    <button
                      v-if="!plugin.builtin"
                      class="btn-danger"
                      @click="deletePlugin(plugin)"
                    >
                      {{ t('settings.pluginDelete') }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="settings-section" :ref="(el) => setSectionRef('account', el)">
          <div class="settings-section-head">
            <h2>{{ t('settings.sectionAccount') }}</h2>
          </div>

          <div class="setting-row">
            <div class="setting-info">
              <h3>{{ t('settings.avatar') }}</h3>
              <p>{{ t('settings.avatarDesc') }}</p>
            </div>
            <div class="setting-control">
              <div class="avatar-section">
                <div class="avatar-circle">
                  <img v-if="getAvatarUrl()" :src="getAvatarUrl()" alt="avatar" class="avatar-img" />
                  <span v-else class="avatar-initials">{{ getInitials() }}</span>
                </div>
                <label class="btn-upload">
                  <input type="file" accept="image/*" @change="uploadAvatar" hidden />
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  {{ getAvatarUrl() ? t('settings.changeAvatar') : t('settings.uploadAvatar') }}
                </label>
              </div>
            </div>
          </div>

          <div class="setting-row setting-row-column">
            <div class="setting-info">
              <h3>{{ t('settings.changePassword') }}</h3>
              <p>{{ t('settings.changePasswordDesc') }}</p>
            </div>
            <div class="setting-control-full">
              <div class="password-form">
                <input
                  v-model="oldPassword"
                  type="password"
                  class="setting-input"
                  :placeholder="t('settings.currentPassword')"
                />
                <input
                  v-model="newPassword"
                  type="password"
                  class="setting-input"
                  :placeholder="t('settings.newPassword')"
                />
                <input
                  v-model="confirmPassword"
                  type="password"
                  class="setting-input"
                  :placeholder="t('settings.confirmPassword')"
                />
                <div class="password-actions">
                  <button class="btn-primary" @click="changePassword">
                    {{ t('settings.changePassword') }}
                  </button>
                </div>
                <p v-if="passwordError" class="msg-error">{{ passwordError }}</p>
                <p v-if="passwordSuccess" class="msg-success">{{ t('settings.passwordChanged') }}</p>
              </div>
            </div>
          </div>
        </section>
      </section>
    </main>
  </div>
</template>

<style scoped>
.settings-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 52px;
  background: var(--bg-deep);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text);
}

.page-title {
  font-weight: 700;
  font-size: 16px;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username {
  color: var(--subtext);
  font-size: 13px;
}

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  background: transparent;
  border: none;
  border-radius: var(--radius);
  color: var(--subtext);
  cursor: pointer;
  transition: all var(--transition);
}

.btn-icon:hover {
  background: var(--surface);
  color: var(--text);
}

.settings-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 180px minmax(0, 760px);
  justify-content: center;
  gap: 32px;
  overflow-y: auto;
  padding: 32px 24px;
  width: 100%;
  box-sizing: border-box;
}

.settings-sidebar {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-self: start;
  position: sticky;
  top: 0;
}

.settings-nav-item {
  width: 100%;
  min-height: 34px;
  padding: 0 12px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius);
  color: var(--subtext);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: all var(--transition);
}

.settings-nav-item:hover {
  background: var(--surface);
  color: var(--text);
}

.settings-nav-item.active {
  background: var(--surface);
  border-color: var(--border);
  color: var(--accent);
}

.settings-content {
  min-width: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.settings-section {
  scroll-margin-top: 16px;
}

.settings-section-head {
  padding: 0 0 12px 0;
  border-bottom: 1px solid var(--border);
}

.settings-section-head h2 {
  margin: 0;
  color: var(--text);
  font-size: 18px;
  font-weight: 700;
}

/* Setting rows */
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 0;
  border-bottom: 1px solid var(--border);
  gap: 24px;
}

@media (max-width: 760px) {
  .settings-layout {
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding: 20px 16px;
  }

  .settings-sidebar {
    position: static;
    flex-direction: row;
    overflow-x: auto;
    padding-bottom: 2px;
  }

  .settings-nav-item {
    width: auto;
    flex: 0 0 auto;
    white-space: nowrap;
  }
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-row-column {
  flex-direction: column;
  align-items: flex-start;
}

.setting-info h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin: 0 0 4px 0;
}

.setting-info p {
  font-size: 13px;
  color: var(--subtext);
  margin: 0;
  line-height: 1.4;
}

.setting-control {
  flex-shrink: 0;
}

.setting-control-full {
  width: 100%;
  margin-top: 12px;
}

/* Theme selector (pill toggle) */
.theme-selector {
  display: flex;
  align-items: center;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2px;
  gap: 1px;
}

.theme-selector button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 28px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--overlay);
  cursor: pointer;
  transition: all var(--transition);
}

.theme-selector button:hover:not(.active) {
  color: var(--subtext);
  background: var(--surface);
}

.theme-selector button.active {
  background: var(--accent);
  color: white;
}

/* Color presets */
.color-presets {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.color-preset {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition);
  padding: 0;
}

.color-preset:hover {
  transform: scale(1.1);
}

.color-preset.active {
  border-color: var(--text);
  box-shadow: 0 0 0 2px var(--bg), 0 0 0 4px var(--text);
}

.color-custom {
  position: relative;
  width: 28px;
  height: 28px;
  cursor: pointer;
}

.color-custom input {
  position: absolute;
  inset: 0;
  opacity: 0;
  width: 100%;
  height: 100%;
  cursor: pointer;
  border: none;
  padding: 0;
}

.color-custom-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px dashed var(--border);
  color: var(--subtext);
  pointer-events: none;
}

.custom-theme-row {
  gap: 0;
}

.custom-theme-mode-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.custom-theme-mode {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.custom-theme-mode h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.custom-theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
}

.theme-color-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.theme-color-field > span {
  font-size: 12px;
  color: var(--subtext);
}

.theme-color-control {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 6px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.theme-color-control input {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
}

.theme-color-control code {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text);
}

.custom-theme-actions {
  margin-top: 12px;
}

/* Select */
.setting-select {
  padding: 7px 32px 7px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 13px;
  outline: none;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  transition: border-color var(--transition);
}

.setting-select:hover {
  border-color: var(--accent);
}

.setting-select:focus {
  border-color: var(--accent);
}

.setting-select option {
  background: var(--surface);
  color: var(--text);
}

/* Text input */
.setting-input {
  width: 100%;
  padding: 9px 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 13px;
  outline: none;
  transition: border-color var(--transition);
  box-sizing: border-box;
}

.setting-input:focus {
  border-color: var(--accent);
}

.setting-input-number {
  width: 80px;
}

/* Tab format */
.format-preview {
  margin-top: 8px;
  font-size: 12px;
  color: var(--subtext);
}

.preview-label {
  margin-right: 4px;
}

.preview-value {
  color: var(--accent);
  font-weight: 500;
}

.format-hint {
  margin-top: 6px;
  display: flex;
  gap: 6px;
}

.format-hint code {
  font-size: 11px;
  padding: 2px 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--subtext);
  font-family: var(--font-mono);
}

/* Avatar */
.avatar-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar-circle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-initials {
  color: white;
  font-size: 18px;
  font-weight: 700;
}

.btn-upload {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition);
  white-space: nowrap;
}

.btn-upload:hover {
  background: var(--surface-hover);
  border-color: var(--accent);
}

.btn-upload.disabled {
  opacity: 0.6;
  pointer-events: none;
}

/* Plugins */
.plugin-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.plugin-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.plugin-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 0;
  border-bottom: 1px solid var(--border);
}

.plugin-item:last-child {
  border-bottom: none;
}

.plugin-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plugin-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.plugin-title-row h4 {
  margin: 0;
  color: var(--text);
  font-size: 14px;
  font-weight: 700;
}

.plugin-badge,
.plugin-status,
.plugin-permission {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 7px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid var(--border);
  color: var(--subtext);
  background: var(--bg);
}

.plugin-badge.builtin {
  color: var(--accent);
}

.plugin-status.enabled {
  color: var(--success, #10b981);
}

.plugin-status.disabled,
.plugin-status.installed {
  color: var(--subtext);
}

.plugin-status.error {
  color: var(--error, #ef4444);
}

.plugin-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  color: var(--subtext);
  font-size: 12px;
}

.plugin-meta code {
  color: var(--text);
  font-family: var(--font-mono);
}

.plugin-description {
  margin: 0;
  color: var(--subtext);
  font-size: 13px;
  line-height: 1.4;
}

.plugin-permissions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.plugin-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.plugin-empty {
  color: var(--subtext);
  font-size: 13px;
}

.plugin-settings-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (max-width: 760px) {
  .plugin-item {
    flex-direction: column;
  }

  .plugin-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}

/* Password form */
.password-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 360px;
}

.password-actions {
  margin-top: 4px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  background: var(--accent);
  border: none;
  border-radius: var(--radius);
  color: white;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition);
}

.btn-primary:hover {
  background: var(--accent-hover);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition);
}

.btn-secondary:hover {
  background: var(--surface-hover);
  border-color: var(--accent);
}

.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.35);
  border-radius: var(--radius);
  color: var(--error, #ef4444);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition);
}

.btn-danger:hover {
  background: rgba(239, 68, 68, 0.14);
  border-color: var(--error, #ef4444);
}

.btn-secondary:disabled,
.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary:disabled:hover,
.btn-danger:disabled:hover {
  background: var(--surface);
  border-color: var(--border);
}

.msg-error {
  font-size: 13px;
  color: var(--error, #ef4444);
  margin: 0;
}

.msg-success {
  font-size: 13px;
  color: var(--success, #10b981);
  margin: 0;
}

/* Toggle group (sidebar position) */
.toggle-group {
  display: flex;
  align-items: center;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2px;
  gap: 1px;
}

.toggle-group button {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--overlay);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--transition);
  white-space: nowrap;
}

.toggle-group button:hover:not(.active) {
  color: var(--subtext);
  background: var(--surface);
}

.toggle-group button.active {
  background: var(--accent);
  color: white;
}

/* Timeout controls */
.timeout-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.timeout-unit {
  font-size: 13px;
  color: var(--subtext);
}

.timeout-presets {
  display: flex;
  gap: 6px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.timeout-preset {
  padding: 5px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--transition);
}

.timeout-preset:hover {
  border-color: var(--accent);
}

.timeout-preset.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

/* Toggle switch */
.switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--surface-hover);
  border-radius: 22px;
  transition: var(--transition);
}

.slider:before {
  position: absolute;
  content: '';
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background: white;
  border-radius: 50%;
  transition: var(--transition);
}

.switch input:checked + .slider {
  background: var(--accent);
}

.switch input:checked + .slider:before {
  transform: translateX(18px);
}

/* Checkbox group */
.checkbox-group {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text);
  cursor: pointer;
}

.checkbox-label input[type='checkbox'] {
  width: 16px;
  height: 16px;
  accent-color: var(--accent);
  cursor: pointer;
}

/* Status bar items list */
.statusbar-items-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.statusbar-item-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  transition: all 0.15s ease;
  cursor: grab;
}

.statusbar-item-row:active {
  cursor: grabbing;
}

.statusbar-item-row.dragging {
  opacity: 0.5;
  background: var(--surface-hover);
}

.statusbar-item-row.drag-over {
  border-color: var(--accent);
  border-style: dashed;
}

.drag-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 20px;
  color: var(--text-secondary);
  opacity: 0.5;
  flex-shrink: 0;
}

.statusbar-item-row:hover .drag-handle {
  opacity: 1;
}

.position-select {
  padding: 4px 8px;
  font-size: 12px;
  background: var(--surface-hover);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 4px;
  cursor: pointer;
  margin-left: auto;
}

.position-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
