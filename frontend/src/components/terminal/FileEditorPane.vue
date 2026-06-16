<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import api from '../../services/api'
import { useSettingsStore } from '../../stores/settings'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  item: { type: Object, required: true },
  position: { type: String, default: 'right' }
})

const emit = defineEmits(['close', 'dirty-change'])

const { t } = useI18n()
const settingsStore = useSettingsStore()

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const content = ref('')
const originalContent = ref('')
const metadata = ref(null)
const mode = ref('info')
const imageUrl = ref('')
const saveTimer = ref(null)
const lastSavedAt = ref(null)
const editorWidth = ref(420)
const isResizing = ref(false)
let resizeStartX = 0
let resizeStartWidth = 0

const isLeft = computed(() => props.position === 'left')
const isDirty = computed(() => mode.value === 'text' && content.value !== originalContent.value)
const title = computed(() => metadata.value?.name || props.item?.name || '')
const statusText = computed(() => {
  if (loading.value) return t('fileEditor.loading')
  if (saving.value) return t('fileEditor.saving')
  if (error.value) return error.value
  if (isDirty.value) return t('fileEditor.unsaved')
  if (lastSavedAt.value) return t('fileEditor.saved')
  return mode.value === 'text' ? t('fileEditor.ready') : t('fileEditor.readOnly')
})

watch(() => props.item?.path, () => {
  openItem()
}, { immediate: true })

watch(isDirty, (dirty) => {
  emit('dirty-change', dirty)
}, { immediate: true })

watch(content, () => {
  if (!settingsStore.fileAutoSave || !isDirty.value || mode.value !== 'text') return
  clearSaveTimer()
  saveTimer.value = setTimeout(() => {
    saveFile()
  }, 900)
})

onBeforeUnmount(() => {
  clearSaveTimer()
  revokeImageUrl()
  stopResize()
})

function clearSaveTimer() {
  if (saveTimer.value) {
    clearTimeout(saveTimer.value)
    saveTimer.value = null
  }
}

function revokeImageUrl() {
  if (imageUrl.value) {
    URL.revokeObjectURL(imageUrl.value)
    imageUrl.value = ''
  }
}

async function openItem() {
  if (mode.value === 'text' && isDirty.value) {
    if (!settingsStore.fileAutoSave && !window.confirm(t('fileEditor.discardConfirm'))) {
      return
    }
    if (settingsStore.fileAutoSave) {
      await saveFile()
      if (isDirty.value || error.value) return
    }
  }

  clearSaveTimer()
  revokeImageUrl()
  loading.value = true
  saving.value = false
  error.value = ''
  content.value = ''
  originalContent.value = ''
  metadata.value = props.item
  lastSavedAt.value = null

  if (props.item?.is_text) {
    await openTextFile()
  } else if (props.item?.mime?.startsWith('image/')) {
    await openImageFile()
  } else {
    mode.value = 'info'
  }
  loading.value = false
}

async function openTextFile() {
  try {
    const { data } = await api.get('/api/files/read', { params: { path: props.item.path } })
    mode.value = 'text'
    metadata.value = data
    originalContent.value = data.content
    content.value = data.content
  } catch (err) {
    const status = err.response?.status
    if (status === 415 && props.item?.mime?.startsWith('image/')) {
      await openImageFile()
      return
    }
    mode.value = 'info'
    error.value = err.response?.data?.detail || t('fileEditor.openFailed')
  }
}

async function openImageFile() {
  mode.value = 'image'
  const token = localStorage.getItem('access_token')
  imageUrl.value = `/api/files/download-browse?path=${encodeURIComponent(props.item.path)}&token=${token}`
}

async function saveFile() {
  if (mode.value !== 'text' || !isDirty.value || saving.value) return
  clearSaveTimer()
  saving.value = true
  error.value = ''
  try {
    const { data } = await api.put('/api/files/write', {
      path: metadata.value.path,
      content: content.value,
      mtime: metadata.value.mtime
    })
    metadata.value = { ...metadata.value, ...data }
    originalContent.value = content.value
    lastSavedAt.value = new Date()
  } catch (err) {
    error.value = err.response?.data?.detail || t('fileEditor.saveFailed')
  } finally {
    saving.value = false
  }
}

async function closePane() {
  if (isDirty.value) {
    if (settingsStore.fileAutoSave) {
      await saveFile()
      if (isDirty.value || error.value) return
    } else if (!window.confirm(t('fileEditor.discardConfirm'))) {
      return
    }
  }
  emit('close')
}

function handleKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    saveFile()
  }
}

function startResize(e) {
  isResizing.value = true
  resizeStartX = e.clientX
  resizeStartWidth = editorWidth.value
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function onResize(e) {
  const diff = isLeft.value ? e.clientX - resizeStartX : resizeStartX - e.clientX
  editorWidth.value = Math.max(260, Math.min(760, resizeStartWidth + diff))
}

function stopResize() {
  if (!isResizing.value) return
  isResizing.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}
</script>

<template>
  <aside
    class="file-editor"
    :class="{ 'is-left': isLeft, resizing: isResizing }"
    :style="{ width: editorWidth + 'px' }"
  >
    <div class="fe-resize-handle" @mousedown="startResize"></div>

    <header class="fe-header">
      <div class="fe-title">
        <span class="fe-name">{{ title }}</span>
        <span class="fe-path">{{ metadata?.path || item.path }}</span>
      </div>
      <div class="fe-actions">
        <button
          v-if="mode === 'text'"
          class="fe-btn"
          :disabled="!isDirty || saving"
          @click="saveFile"
          :title="t('fileEditor.save')"
        >
          {{ t('fileEditor.save') }}
        </button>
        <button class="fe-icon-btn" @click="closePane" :title="t('fileEditor.close')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </header>

    <div class="fe-status" :class="{ error: !!error, dirty: isDirty }">
      {{ statusText }}
    </div>

    <div class="fe-body">
      <div v-if="loading" class="fe-empty">{{ t('fileEditor.loading') }}</div>

      <textarea
        v-else-if="mode === 'text'"
        v-model="content"
        class="fe-textarea"
        spellcheck="false"
        @keydown="handleKeydown"
      />

      <div v-else-if="mode === 'image'" class="fe-image-wrap">
        <img :src="imageUrl" :alt="title" />
      </div>

      <div v-else class="fe-empty">
        <div class="fe-empty-title">{{ t('fileEditor.readOnly') }}</div>
        <div class="fe-empty-detail">{{ metadata?.mime || item.mime || t('fileEditor.unknownType') }}</div>
        <div v-if="metadata?.size || item.size" class="fe-empty-detail">
          {{ Math.round((metadata?.size || item.size) / 1024) }} KB
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.file-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  background: var(--bg);
  border-left: 1px solid var(--border);
  border-right: 1px solid var(--border);
  min-width: 0;
  position: relative;
}

.file-editor.is-left {
  border-left: none;
}

.file-editor.resizing {
  transition: none;
}

.fe-resize-handle {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: col-resize;
  z-index: 10;
  transition: background 0.15s;
}

.file-editor.is-left .fe-resize-handle {
  left: auto;
  right: 0;
}

.fe-resize-handle:hover,
.file-editor.resizing .fe-resize-handle {
  background: var(--accent);
}

.fe-header {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 10px 6px 12px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-deep);
}

.fe-title {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.fe-name {
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fe-path {
  color: var(--overlay);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fe-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.fe-btn,
.fe-icon-btn {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  border-radius: 4px;
  cursor: pointer;
}

.fe-btn {
  height: 26px;
  padding: 0 10px;
  font-size: 12px;
}

.fe-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.fe-icon-btn {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.fe-btn:hover:not(:disabled),
.fe-icon-btn:hover {
  border-color: var(--accent);
}

.fe-status {
  height: 24px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  border-bottom: 1px solid var(--border);
  color: var(--subtext);
  font-size: 11px;
  background: var(--surface);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fe-status.dirty {
  color: var(--accent);
}

.fe-status.error {
  color: var(--error);
}

.fe-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.fe-textarea {
  width: 100%;
  height: 100%;
  display: block;
  resize: none;
  border: none;
  outline: none;
  padding: 12px;
  box-sizing: border-box;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.55;
  tab-size: 2;
}

.fe-image-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  padding: 12px;
  box-sizing: border-box;
}

.fe-image-wrap img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.fe-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px;
  text-align: center;
  color: var(--subtext);
  box-sizing: border-box;
}

.fe-empty-title {
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
}

.fe-empty-detail {
  max-width: 100%;
  color: var(--overlay);
  font-size: 12px;
  overflow-wrap: anywhere;
}
</style>
