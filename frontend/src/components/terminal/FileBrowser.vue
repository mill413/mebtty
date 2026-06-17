<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { getCatppuccinFileIcon, getCatppuccinFolderIcon } from 'vscode-icon-resolver'
import api from '../../services/api'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  position: { type: String, default: 'right' },
  initialPath: { type: String, default: '' }
})

const emit = defineEmits(['close', 'open-file', 'path-change'])

const isLeft = computed(() => props.position === 'left')

// --- Resize state ---
const sidebarWidth = ref(280)
const isResizing = ref(false)
let resizeStartX = 0
let resizeStartWidth = 0

function startResize(e) {
  isResizing.value = true
  resizeStartX = e.clientX
  resizeStartWidth = sidebarWidth.value
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function onResize(e) {
  const diff = isLeft.value ? e.clientX - resizeStartX : resizeStartX - e.clientX
  const newWidth = resizeStartWidth + diff
  sidebarWidth.value = Math.max(180, Math.min(600, newWidth))
}

function stopResize() {
  isResizing.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

// --- State ---
const currentPath = ref('')           // current working directory (relative to browse root)
const absoluteRoot = ref('')           // absolute path of browse root
const tree = reactive([])              // items at current level
const expandedPaths = reactive(new Set())
const childrenMap = reactive({})       // path -> items[]
const loadingPaths = reactive(new Set())
const selectedItem = ref(null)         // currently selected item (for upload/new-folder target)
const contextMenu = ref({ show: false, x: 0, y: 0, item: null })
const showNewFolderDialog = ref(false)
const newFolderName = ref('')
const newFolderParent = ref('')
const showRenameDialog = ref(false)
const renameItem = ref(null)
const renameNewName = ref('')
const showDeleteConfirm = ref(false)
const deleteItem = ref(null)
const showHidden = ref(false)              // show hidden files (dotfiles)

function fetchDirectory(path) {
  return api.get('/api/files/browse', {
    params: { path: path || '', show_hidden: showHidden.value }
  })
}

// --- Show hidden files toggle ---
async function toggleShowHidden() {
  showHidden.value = !showHidden.value
  // Reload current directory and all expanded subdirectories without collapsing
  await refreshAll(false)
}

// --- Auto-refresh (polling) ---
const AUTO_REFRESH_INTERVAL = 5000 // 5 seconds
let refreshTimer = null
let isRefreshing = false

function startAutoRefresh() {
  stopAutoRefresh()
  refreshTimer = setInterval(autoRefresh, AUTO_REFRESH_INTERVAL)
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

async function autoRefresh() {
  if (isRefreshing) return
  isRefreshing = true
  try {
    // Refresh current directory
    if (currentPath.value !== null && currentPath.value !== undefined) {
      const res = await fetchDirectory(currentPath.value)
      // Preserve selection if the item still exists
      const oldSelected = selectedItem.value
      tree.length = 0
      tree.push(...res.data.items.map(item => ({ ...item, depth: 0 })))
      childrenMap[currentPath.value || ''] = res.data.items

      // Try to restore selection
      if (oldSelected) {
        const stillExists = tree.find(item => item.path === oldSelected.path && item.name === oldSelected.name)
        if (stillExists) {
          selectedItem.value = stillExists
        } else {
          selectedItem.value = null
        }
      }

      // Refresh all expanded subdirectories
      for (const path of expandedPaths) {
        try {
          const childRes = await fetchDirectory(path)
          childrenMap[path] = childRes.data.items
        } catch (err) {
          // Subdirectory may have been deleted — remove from expanded set
          expandedPaths.delete(path)
          delete childrenMap[path]
        }
      }
    }
  } catch (err) {
    console.error('Auto-refresh failed:', err)
  } finally {
    isRefreshing = false
  }
}
const breadcrumbSegments = computed(() => {
  const path = currentPath.value || '/'
  const parts = path.split('/').filter(Boolean)
  const segments = []
  let accumulated = '/'
  for (const part of parts) {
    accumulated = accumulated === '/' ? '/' + part : accumulated + '/' + part
    segments.push({ label: part, path: accumulated })
  }
  return segments
})

// Determine target directory for upload/new-folder
const activeDir = computed(() => {
  if (selectedItem.value && selectedItem.value.is_dir) {
    return selectedItem.value.path
  }
  return currentPath.value
})

onMounted(() => {
  loadDirectory(props.initialPath || '')
  document.addEventListener('click', closeContextMenu)
  startAutoRefresh()
})

onUnmounted(() => {
  document.removeEventListener('click', closeContextMenu)
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  stopAutoRefresh()
})

// --- Directory loading ---
async function loadDirectory(path) {
  loadingPaths.add(path)
  try {
    const res = await fetchDirectory(path)
    // API now returns absolute paths for both path and absolute_path
    const curPath = res.data.path || '/'
    currentPath.value = curPath
    emit('path-change', curPath)
    absoluteRoot.value = '/'

    // Reset tree
    tree.length = 0
    tree.push(...res.data.items.map(item => ({ ...item, depth: 0 })))
    childrenMap[path || ''] = res.data.items

    // Clear stale expanded/children state
    expandedPaths.clear()
    for (const key of Object.keys(childrenMap)) {
      if (key !== (path || '')) delete childrenMap[key]
    }
    selectedItem.value = null
  } catch (err) {
    console.error('Failed to load directory:', err)
  } finally {
    loadingPaths.delete(path)
  }
}

async function loadChildren(item) {
  if (expandedPaths.has(item.path)) {
    expandedPaths.delete(item.path)
    return
  }

  if (childrenMap[item.path]) {
    expandedPaths.add(item.path)
    return
  }

  loadingPaths.add(item.path)
  try {
    const res = await fetchDirectory(item.path)
    childrenMap[item.path] = res.data.items
    expandedPaths.add(item.path)
  } catch (err) {
    console.error('Failed to load children:', err)
  } finally {
    loadingPaths.delete(item.path)
  }
}

// Build flat list with proper depth for rendering
function getFlatList() {
  const result = []
  function addItems(items, depth) {
    for (const item of items) {
      result.push({ ...item, depth })
      if (item.is_dir && expandedPaths.has(item.path)) {
        const children = childrenMap[item.path]
        if (children) {
          addItems(children, depth + 1)
        }
      }
      if (item.is_dir && loadingPaths.has(item.path) && !expandedPaths.has(item.path)) {
        // show loading under a non-yet-expanded dir
      } else if (item.is_dir && loadingPaths.has(item.path) && expandedPaths.has(item.path) && !childrenMap[item.path]) {
        result.push({ name: t('fileBrowser.loading'), depth: depth + 1, is_loading: true, is_dir: false, path: item.path + '/__loading' })
      }
    }
  }
  addItems(tree, 0)
  return result
}

// --- Click handlers ---
function handleClick(item) {
  if (selectedItem.value && selectedItem.value.path === item.path) {
    selectedItem.value = null
    if (item.is_dir) {
      expandedPaths.delete(item.path)
    }
  } else {
    selectedItem.value = item
    if (item.is_dir) {
      loadChildren(item)
    }
  }
}

function handleDblClick(item) {
  if (item.is_dir) {
    loadDirectory(item.path)
  } else {
    emit('open-file', item)
  }
}

function clickBreadcrumb(path) {
  selectedItem.value = null
  loadDirectory(path)
}

// --- File operations ---
function downloadFile(item) {
  const token = localStorage.getItem('access_token')
  const link = document.createElement('a')
  link.href = `/api/files/download-browse?path=${encodeURIComponent(item.path)}&token=${token}`
  link.download = item.name
  link.click()
}

function handleUpload() {
  const targetDir = activeDir.value
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  input.onchange = async (e) => {
    const files = e.target.files
    if (!files.length) return
    for (const file of files) {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('target_dir', targetDir)
      try {
        await api.post('/api/files/upload-browse', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
      } catch (err) {
        console.error('Upload failed:', err)
      }
    }
    await refreshAfter(targetDir)
  }
  input.click()
}

function handleNewFolder() {
  newFolderName.value = ''
  newFolderParent.value = activeDir.value
  showNewFolderDialog.value = true
}

async function createFolder() {
  if (!newFolderName.value.trim()) return
  try {
    const formData = new FormData()
    formData.append('path', newFolderParent.value)
    formData.append('name', newFolderName.value.trim())
    await api.post('/api/files/mkdir', formData)
    showNewFolderDialog.value = false
    await refreshAfter(newFolderParent.value)
  } catch (err) {
    alert(err.response?.data?.detail || t('fileBrowser.failedCreateFolder'))
  }
}

function handleContextMenu(e, item) {
  e.preventDefault()
  selectedItem.value = item
  contextMenu.value = { show: true, x: e.clientX, y: e.clientY, item }
}

function closeContextMenu() {
  contextMenu.value.show = false
}

async function copyPath(item) {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(item.path)
      return
    } catch (err) {
      // Fall through to legacy method
    }
  }
  // Fallback for older browsers or insecure contexts (e.g. via HTTP tunnel)
  const textarea = document.createElement('textarea')
  textarea.value = item.path
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  try {
    document.execCommand('copy')
  } catch {}
  document.body.removeChild(textarea)
}

function promptRename(item) {
  renameItem.value = item
  renameNewName.value = item.name
  showRenameDialog.value = true
}

async function rename() {
  if (!renameNewName.value.trim() || !renameItem.value) return
  try {
    const formData = new FormData()
    formData.append('path', renameItem.value.path)
    formData.append('new_name', renameNewName.value.trim())
    await api.post('/api/files/rename', formData)
    showRenameDialog.value = false
    await refreshParent(renameItem.value)
  } catch (err) {
    alert(err.response?.data?.detail || t('fileBrowser.failedRename'))
  }
}

function promptDelete(item) {
  deleteItem.value = item
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  if (!deleteItem.value) return
  try {
    const formData = new FormData()
    formData.append('path', deleteItem.value.path)
    await api.post('/api/files/delete', formData)
    showDeleteConfirm.value = false
    expandedPaths.delete(deleteItem.value.path)
    await refreshParent(deleteItem.value)
  } catch (err) {
    alert(err.response?.data?.detail || t('fileBrowser.failedDelete'))
  }
}

// --- Refresh helpers ---
async function refreshAfter(path) {
  if (path === currentPath.value || path === '') {
    // Refresh current tree root
    await loadDirectory(currentPath.value)
    return
  }
  // Refresh a subdirectory's children
  try {
    const res = await fetchDirectory(path)
    childrenMap[path] = res.data.items
  } catch (err) {
    console.error('Failed to refresh:', err)
  }
}

async function refreshAll(clearSelection = true) {
  try {
    // Reload current directory
    const res = await fetchDirectory(currentPath.value)
    tree.length = 0
    tree.push(...res.data.items.map(item => ({ ...item, depth: 0 })))
    childrenMap[currentPath.value || ''] = res.data.items

    if (clearSelection) {
      selectedItem.value = null
    }

    // Reload all expanded subdirectories
    for (const path of expandedPaths) {
      try {
        const childRes = await fetchDirectory(path)
        childrenMap[path] = childRes.data.items
      } catch (err) {
        expandedPaths.delete(path)
        delete childrenMap[path]
      }
    }
  } catch (err) {
    console.error('Failed to reload directory:', err)
  }
}

async function refreshParent(item) {
  const parts = item.path.split('/')
  parts.pop()
  const parentPath = parts.join('/')
  return refreshAfter(parentPath)
}

// --- Icon helpers (Catppuccin VSCode Icons) ---
function getFileIconSrc(item) {
  if (item.is_dir) {
    const isOpen = expandedPaths.has(item.path)
    const iconName = getCatppuccinFolderIcon(item.name)
    if (iconName.startsWith('_')) {
      return `/catppuccin-icons/${isOpen ? iconName + '_open' : iconName}.svg`
    }
    return `/catppuccin-icons/folder_${iconName}${isOpen ? '_open' : ''}.svg`
  }
  const iconName = getCatppuccinFileIcon(item.name)
  return `/catppuccin-icons/${iconName}.svg`
}

function onIconError(e) {
  e.target.src = '/catppuccin-icons/_file.svg'
}

function getIndentStyle(depth) {
  return { paddingLeft: (8 + depth * 16) + 'px' }
}
</script>

<template>
  <div
    class="file-browser"
    :class="{ resizing: isResizing, 'is-left': isLeft }"
    :style="{ width: sidebarWidth + 'px' }"
  >
    <div class="fb-resize-handle" @mousedown="startResize"></div>

    <div class="fb-header">
      <div class="fb-title">
        <span>{{ t('fileBrowser.explorer') }}</span>
      </div>
      <div class="fb-actions">
        <button class="fb-btn-icon" @click="handleUpload" :title="t('fileBrowser.upload')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </button>
        <button class="fb-btn-icon" @click="handleNewFolder" :title="t('fileBrowser.newFolder')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
            <line x1="12" y1="11" x2="12" y2="17"/>
            <line x1="9" y1="14" x2="15" y2="14"/>
          </svg>
        </button>
        <button class="fb-btn-icon" @click="toggleShowHidden" :class="{ active: showHidden }" :title="t('fileBrowser.showHidden')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
            <line x1="1" y1="1" x2="23" y2="23"/>
          </svg>
        </button>
        <button class="fb-btn-icon" @click="loadDirectory(currentPath)" :title="t('fileBrowser.refresh')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Breadcrumb navigation -->
    <div class="fb-breadcrumb">
      <span class="fb-bc-home" @click="clickBreadcrumb('/')" title="/">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="fb-bc-icon">
          <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
      </span>
      <span class="fb-bc-sep">/</span>
      <template v-for="(seg, i) in breadcrumbSegments" :key="seg.path + '-' + i">
        <span
          class="fb-bc-segment"
          :class="{ active: seg.path === currentPath }"
          @click="clickBreadcrumb(seg.path)"
        >{{ seg.label }}</span>
        <span v-if="i < breadcrumbSegments.length - 1" class="fb-bc-sep">/</span>
      </template>
    </div>

    <!-- Tree view -->
    <div class="fb-tree" @click.self="selectedItem = null">
      <template v-for="item in getFlatList()" :key="item.path || item.name">
        <div
          v-if="!item.is_loading"
          class="fb-tree-item"
          :class="{
            'is-selected': selectedItem && selectedItem.path === item.path,
            'is-dir': item.is_dir,
            'is-inaccessible': !item.accessible
          }"
          :style="getIndentStyle(item.depth)"
          @click="item.accessible && handleClick(item)"
          @dblclick="item.accessible && handleDblClick(item)"
          @contextmenu="item.accessible && handleContextMenu($event, item)"
        >
          <!-- Chevron for directories -->
          <span v-if="item.is_dir && item.accessible" class="fb-chevron" :class="{ expanded: expandedPaths.has(item.path) }">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </span>
          <!-- Lock icon for inaccessible directories -->
          <span v-else-if="item.is_dir && !item.accessible" class="fb-lock-icon">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0110 0v4"/>
            </svg>
          </span>
          <span v-else class="fb-chevron-spacer"></span>

          <!-- Icon (Catppuccin) -->
          <span class="fb-icon">
            <img
              :src="getFileIconSrc(item)"
              :alt="item.name"
              width="18"
              height="18"
              @error="onIconError"
              draggable="false"
            />
          </span>

          <span class="fb-name">{{ item.name }}</span>
        </div>

        <!-- Loading indicator -->
        <div
          v-else
          class="fb-tree-item fb-loading-item"
          :style="getIndentStyle(item.depth)"
        >
          <span class="fb-chevron-spacer"></span>
          <span class="fb-loading-dots">{{ t('fileBrowser.loading') }}</span>
        </div>
      </template>

      <div v-if="tree.length === 0 && !loadingPaths.has(currentPath)" class="fb-empty">
        {{ t('fileBrowser.emptyDir') }}
      </div>
    </div>

    <!-- Context Menu -->
    <Teleport to="body">
      <div
        v-if="contextMenu.show"
        class="fb-context-menu"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
      >
        <button v-if="contextMenu.item && !contextMenu.item.is_dir" @click="downloadFile(contextMenu.item); closeContextMenu()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          {{ t('fileBrowser.download') }}
        </button>
        <button v-if="contextMenu.item && contextMenu.item.is_dir" @click="promptRename(contextMenu.item); closeContextMenu()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
            <line x1="12" y1="11" x2="12" y2="17"/>
            <line x1="9" y1="14" x2="15" y2="14"/>
          </svg>
          {{ t('fileBrowser.newFolderHere') }}
        </button>
        <button @click="copyPath(contextMenu.item); closeContextMenu()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
          </svg>
          {{ t('fileBrowser.copyPath') }}
        </button>
        <button @click="promptRename(contextMenu.item); closeContextMenu()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          {{ t('fileBrowser.rename') }}
        </button>
        <button class="danger" @click="promptDelete(contextMenu.item); closeContextMenu()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
          </svg>
          {{ t('fileBrowser.delete') }}
        </button>
      </div>
    </Teleport>

    <!-- New Folder Dialog -->
    <Teleport to="body">
      <div v-if="showNewFolderDialog" class="fb-dialog-overlay" @click.self="showNewFolderDialog = false">
        <div class="fb-dialog">
          <h3>{{ t('fileBrowser.newFolderTitle') }}</h3>
          <input
            v-model="newFolderName"
            type="text"
            :placeholder="t('fileBrowser.folderNamePlaceholder')"
            @keyup.enter="createFolder"
            autofocus
          />
          <div class="fb-dialog-actions">
            <button class="fb-btn-cancel" @click="showNewFolderDialog = false">{{ t('fileBrowser.cancel') }}</button>
            <button class="fb-btn-confirm" @click="createFolder">{{ t('fileBrowser.create') }}</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Rename Dialog -->
    <Teleport to="body">
      <div v-if="showRenameDialog" class="fb-dialog-overlay" @click.self="showRenameDialog = false">
        <div class="fb-dialog">
          <h3>{{ t('fileBrowser.renameTitle') }}</h3>
          <input
            v-model="renameNewName"
            type="text"
            @keyup.enter="rename"
            autofocus
          />
          <div class="fb-dialog-actions">
            <button class="fb-btn-cancel" @click="showRenameDialog = false">{{ t('fileBrowser.cancel') }}</button>
            <button class="fb-btn-confirm" @click="rename">{{ t('fileBrowser.rename') }}</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirm -->
    <Teleport to="body">
      <div v-if="showDeleteConfirm" class="fb-dialog-overlay" @click.self="showDeleteConfirm = false">
        <div class="fb-dialog">
          <h3>{{ deleteItem?.is_dir ? t('fileBrowser.deleteFolder') : t('fileBrowser.deleteFile') }}</h3>
          <p>{{ t('fileBrowser.deleteConfirm', { name: deleteItem?.name }) }}</p>
          <div class="fb-dialog-actions">
            <button class="fb-btn-cancel" @click="showDeleteConfirm = false">{{ t('fileBrowser.cancel') }}</button>
            <button class="fb-btn-danger" @click="confirmDelete">{{ t('fileBrowser.delete') }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.file-browser {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-deep);
  border-left: 1px solid var(--border);
  flex-shrink: 0;
  position: relative;
  user-select: none;
}

.file-browser.is-left {
  border-left: none;
  border-right: 1px solid var(--border);
}

.file-browser.resizing {
  transition: none;
}

.fb-resize-handle {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: col-resize;
  z-index: 10;
  transition: background 0.15s;
}

.file-browser.is-left .fb-resize-handle {
  left: auto;
  right: 0;
}

.fb-resize-handle:hover,
.file-browser.resizing .fb-resize-handle {
  background: var(--accent);
}

/* Header */
.fb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px 6px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.fb-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--subtext);
  text-transform: uppercase;
}

.fb-actions {
  display: flex;
  gap: 2px;
}

.fb-btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--subtext);
  transition: all var(--transition);
}

.fb-btn-icon:hover {
  background: var(--surface);
  color: var(--text);
}

.fb-btn-icon.active {
  background: var(--surface);
  color: var(--accent);
}

/* Breadcrumb */
.fb-breadcrumb {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 5px 12px 5px 16px;
  font-size: 12px;
  color: var(--subtext);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  font-family: var(--font-mono);
  overflow-x: auto;
  white-space: nowrap;
  cursor: default;
}

.fb-breadcrumb::-webkit-scrollbar {
  height: 0;
}

.fb-bc-icon {
  flex-shrink: 0;
  margin-right: 4px;
  color: var(--subtext);
}

.fb-bc-home {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 1px 3px;
  border-radius: 3px;
  flex-shrink: 0;
  transition: all 0.1s;
}

.fb-bc-home:hover {
  background: var(--surface);
  color: var(--text);
}

.fb-bc-segment {
  cursor: pointer;
  padding: 1px 3px;
  border-radius: 3px;
  transition: all 0.1s;
  flex-shrink: 0;
}

.fb-bc-segment:hover {
  background: var(--surface);
  color: var(--text);
}

.fb-bc-segment.active {
  color: var(--text);
  font-weight: 600;
}

.fb-bc-sep {
  color: var(--overlay);
  flex-shrink: 0;
}

/* Tree */
.fb-tree {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 2px 0;
}

.fb-tree-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  cursor: pointer;
  transition: background 0.1s;
  white-space: nowrap;
  font-size: 13px;
  line-height: 22px;
}

.fb-tree-item:hover {
  background: var(--surface);
}

.fb-tree-item.is-selected {
  background: rgba(124, 58, 237, 0.15);
}

.fb-chevron {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  transition: transform 0.15s;
  color: var(--subtext);
}

.fb-chevron.expanded {
  transform: rotate(90deg);
}

.fb-chevron-spacer {
  width: 16px;
  flex-shrink: 0;
}

.fb-lock-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: var(--overlay);
}

.fb-tree-item.is-inaccessible {
  opacity: 0.5;
  cursor: not-allowed !important;
}

.fb-tree-item.is-inaccessible:hover {
  background: transparent;
}

.fb-tree-item.is-inaccessible .fb-name {
  color: var(--subtext);
}

.fb-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

/* Catppuccin icons have built-in colors, no overrides needed */

.fb-name {
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fb-loading-item {
  color: var(--subtext);
  font-style: italic;
}

.fb-loading-dots {
  font-size: 12px;
  color: var(--subtext);
}

.fb-empty {
  padding: 20px;
  text-align: center;
  color: var(--subtext);
  font-size: 13px;
}

/* Context menu */
.fb-context-menu {
  position: fixed;
  z-index: 1000;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 4px;
  min-width: 160px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.fb-context-menu button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: var(--text);
  font-size: 13px;
  text-align: left;
  transition: background 0.1s;
}

.fb-context-menu button:hover {
  background: var(--overlay);
}

.fb-context-menu button.danger {
  color: var(--error);
}

/* Dialogs */
.fb-dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.fb-dialog {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  min-width: 300px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
}

.fb-dialog h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text);
}

.fb-dialog p {
  font-size: 14px;
  color: var(--subtext);
  margin-bottom: 16px;
}

.fb-dialog input {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 14px;
  margin-bottom: 16px;
}

.fb-dialog input:focus {
  outline: none;
  border-color: var(--accent);
}

.fb-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.fb-btn-cancel, .fb-btn-confirm, .fb-btn-danger {
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 500;
  transition: all var(--transition);
}

.fb-btn-cancel {
  background: var(--bg);
  color: var(--text);
}

.fb-btn-cancel:hover {
  background: var(--overlay);
}

.fb-btn-confirm {
  background: var(--accent);
  color: white;
}

.fb-btn-confirm:hover {
  background: var(--accent-hover);
}

.fb-btn-danger {
  background: var(--error);
  color: white;
}

.fb-btn-danger:hover {
  opacity: 0.9;
}
</style>
