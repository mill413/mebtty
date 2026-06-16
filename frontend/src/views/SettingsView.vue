<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '../stores/settings'
import { useThemeStore } from '../stores/theme'
import { useAuthStore } from '../stores/auth'
import { setLocale, resetToBrowserLocale, getSupportedLocales, hasUserLocale } from '../i18n'
import api from '../services/api'

const props = defineProps({
  embedded: { type: Boolean, default: false }
})

const { t, locale: i18nLocale } = useI18n()
const router = useRouter()
const settingsStore = useSettingsStore()
const themeStore = useThemeStore()
const authStore = useAuthStore()

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
const customColor = ref('')
const tabFormat = ref('')
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordError = ref('')
const passwordSuccess = ref(false)

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
  customColor.value = settingsStore.accentColor
  tabFormat.value = settingsStore.tabTitleFormat
})

function changeTheme(mode) {
  themeStore.setMode(mode)
  settingsStore.updateSettings({ theme_mode: mode })
}

function changeAccentColor(color) {
  customColor.value = color
  settingsStore.accentColor = color
  settingsStore.applyAccentColor()
  settingsStore.updateSettings({ accent_color: color })
}

function onCustomColorInput(e) {
  changeAccentColor(e.target.value)
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

    <main class="settings-content">
      <!-- Language -->
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

      <!-- Color Mode -->
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

      <!-- Accent Color -->
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
              :class="{ active: settingsStore.accentColor === color }"
              :style="{ background: color }"
              @click="changeAccentColor(color)"
            >
              <svg v-if="settingsStore.accentColor === color" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </button>
            <label class="color-custom" :title="t('settings.accentColor')">
              <input type="color" :value="customColor" @input="onCustomColorInput" />
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

      <!-- Tab Title Format -->
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

      <!-- Status Bar -->
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

      <!-- File Auto Save -->
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

      <!-- Status Bar Items -->
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

      <!-- User Avatar -->
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

      <!-- Change Password -->
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

      <!-- Sidebar Position -->
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

      <!-- Session Timeout -->
      <div class="setting-row setting-row-column">
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

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 32px 24px;
  max-width: 700px;
  width: 100%;
  margin: 0 auto;
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
