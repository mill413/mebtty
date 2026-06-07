<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useTerminalStore } from '../stores/terminal'
import ThemeToggle from '../components/common/ThemeToggle.vue'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const terminalStore = useTerminalStore()

const showShellDialog = ref(false)
const selectedShell = ref('/bin/bash')
const sessionTitle = ref('')
const sessionCwd = ref('')
const creating = ref(false)

const shells = [
  { value: '/bin/bash', label: 'Bash', icon: '⚡' },
  { value: '/bin/zsh', label: 'Zsh', icon: '🔷' },
  { value: '/usr/bin/fish', label: 'Fish', icon: '🐟' },
  { value: '/bin/sh', label: 'SH', icon: '📟' }
]

const runningSessions = computed(() =>
  terminalStore.sessions.filter((s) => s.status === 'running')
)

const recentSessions = computed(() =>
  terminalStore.sessions.slice(0, 10)
)

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchUser()
  }
  await terminalStore.fetchSessions()
})

async function createNewSession() {
  creating.value = true
  try {
    await terminalStore.createSession(selectedShell.value, sessionTitle.value, sessionCwd.value)
    showShellDialog.value = false
    sessionTitle.value = ''
    sessionCwd.value = ''
  } catch (err) {
    console.error('Failed to create session:', err)
  } finally {
    creating.value = false
  }
}

async function reconnectToSession(sessionId) {
  try {
    await terminalStore.reconnectSession(sessionId)
  } catch (err) {
    console.error('Failed to reconnect:', err)
  }
}

function openTerminal() {
  if (terminalStore.tabs.length > 0) {
    const tab = terminalStore.activeTab || terminalStore.tabs[0]
    router.push(`/terminal/${tab.sessionId}`)
  } else {
    showShellDialog.value = true
  }
}

function logout() {
  authStore.logout()
  router.push('/login')
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<template>
  <div class="home-page">
    <header class="top-bar">
      <div class="top-bar-left">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="4 17 10 11 4 5" />
          <line x1="12" y1="19" x2="20" y2="19" />
        </svg>
        <span class="brand">WebTTY</span>
      </div>
      <div class="top-bar-right">
        <ThemeToggle />
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

    <main class="home-content">
      <section class="welcome-section fade-in">
        <h1>{{ t('home.welcome') }} <span class="accent">{{ authStore.username }}</span></h1>
        <p class="text-subtext">{{ t('home.subtitle') }}</p>
      </section>

      <section class="stats-row">
        <div class="stat-card">
          <div class="stat-value">{{ terminalStore.sessions.length }}</div>
          <div class="stat-label text-subtext">{{ t('home.totalSessions') }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-value text-success">{{ runningSessions.length }}</div>
          <div class="stat-label text-subtext">{{ t('home.running') }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ terminalStore.tabs.length }}</div>
          <div class="stat-label text-subtext">{{ t('home.openTabs') }}</div>
        </div>
      </section>

      <section class="actions-section">
        <button class="btn-new-terminal" @click="showShellDialog = true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          {{ t('home.newTerminal') }}
        </button>

        <button v-if="terminalStore.tabs.length > 0" class="btn-open-terminal" @click="openTerminal">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="4 17 10 11 4 5" />
            <line x1="12" y1="19" x2="20" y2="19" />
          </svg>
          {{ t('home.openTerminal') }} ({{ terminalStore.tabs.length }})
        </button>
      </section>

      <section v-if="runningSessions.length > 0" class="sessions-section">
        <h2>{{ t('home.runningSessions') }}</h2>
        <div class="session-list">
          <div
            v-for="session in runningSessions"
            :key="session.id"
            class="session-card session-running"
            @click="reconnectToSession(session.id)"
          >
            <div class="session-info">
              <div class="session-title">
                <span class="status-dot running"></span>
                {{ session.title || session.shell }}
              </div>
              <div class="session-meta text-subtext">
                {{ session.shell }} &middot; {{ formatDate(session.created_at) }}
              </div>
            </div>
            <div class="session-action">
              <span class="badge-running">{{ t('home.running') }}</span>
            </div>
          </div>
        </div>
      </section>

      <section v-if="recentSessions.length > 0" class="sessions-section">
        <h2>{{ t('home.recentSessions') }}</h2>
        <div class="session-list">
          <div
            v-for="session in recentSessions"
            :key="session.id"
            class="session-card"
            @click="reconnectToSession(session.id)"
          >
            <div class="session-info">
              <div class="session-title">
                <span class="status-dot" :class="session.status"></span>
                {{ session.title || session.shell }}
              </div>
              <div class="session-meta text-subtext">
                {{ session.shell }} &middot; {{ formatDate(session.created_at) }}
              </div>
            </div>
            <div class="session-action text-subtext">
              {{ session.status || 'detached' }}
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- Shell selector dialog -->
    <Teleport to="body">
      <div v-if="showShellDialog" class="dialog-overlay" @click.self="showShellDialog = false">
        <div class="dialog-card slide-up">
          <h3>{{ t('home.newSession') }}</h3>

          <div class="form-group">
            <label>{{ t('home.shell') }}</label>
            <div class="shell-grid">
              <button
                v-for="shell in shells"
                :key="shell.value"
                class="shell-option"
                :class="{ active: selectedShell === shell.value }"
                @click="selectedShell = shell.value"
              >
                <span class="shell-icon">{{ shell.icon }}</span>
                <span>{{ shell.label }}</span>
              </button>
            </div>
          </div>

          <div class="form-group">
            <label>{{ t('home.titleOptional') }}</label>
            <input v-model="sessionTitle" type="text" :placeholder="t('home.titlePlaceholder')" />
          </div>

          <div class="form-group">
            <label>{{ t('home.cwdOptional') }}</label>
            <input v-model="sessionCwd" type="text" :placeholder="t('home.cwdPlaceholder')" />
          </div>

          <div class="dialog-actions">
            <button class="btn-secondary" @click="showShellDialog = false">{{ t('home.cancel') }}</button>
            <button class="btn-primary" @click="createNewSession" :disabled="creating">
              {{ creating ? t('home.creating') : t('home.create') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.home-page {
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

.brand {
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
  transition: all var(--transition);
}

.btn-icon:hover {
  background: var(--surface);
  color: var(--text);
}

.home-content {
  flex: 1;
  overflow-y: auto;
  padding: 40px;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.welcome-section {
  margin-bottom: 32px;
}

.welcome-section h1 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 6px;
}

.accent {
  color: var(--accent);
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
}

.actions-section {
  display: flex;
  gap: 12px;
  margin-bottom: 40px;
}

.btn-new-terminal {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 600;
  transition: background var(--transition);
}

.btn-new-terminal:hover {
  background: var(--accent-hover);
}

.btn-open-terminal {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 500;
  transition: all var(--transition);
}

.btn-open-terminal:hover {
  background: var(--surface-hover);
  border-color: var(--accent);
}

.sessions-section {
  margin-bottom: 32px;
}

.sessions-section h2 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 12px;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all var(--transition);
}

.session-card:hover {
  background: var(--surface-hover);
  border-color: var(--accent);
}

.session-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  margin-bottom: 2px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--overlay);
}

.status-dot.running {
  background: var(--success);
  box-shadow: 0 0 6px rgba(166, 227, 161, 0.4);
}

.session-meta {
  font-size: 12px;
  padding-left: 16px;
}

.session-action {
  font-size: 13px;
}

.badge-running {
  display: inline-block;
  padding: 2px 10px;
  background: rgba(166, 227, 161, 0.12);
  color: var(--success);
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

/* Dialog styles */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.dialog-card {
  width: 440px;
  max-width: 90vw;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 28px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.dialog-card h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--subtext);
  margin-bottom: 6px;
}

.form-group input {
  width: 100%;
  padding: 9px 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  outline: none;
  transition: border-color var(--transition);
}

.form-group input:focus {
  border-color: var(--accent);
}

.shell-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.shell-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 13px;
  transition: all var(--transition);
}

.shell-option:hover {
  border-color: var(--accent);
}

.shell-option.active {
  border-color: var(--accent);
  background: rgba(124, 58, 237, 0.12);
}

.shell-icon {
  font-size: 20px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}

.btn-secondary {
  padding: 9px 18px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 13px;
  transition: all var(--transition);
}

.btn-secondary:hover {
  background: var(--bg);
}

.btn-primary {
  padding: 9px 18px;
  background: var(--accent);
  border: none;
  border-radius: var(--radius);
  color: white;
  font-size: 13px;
  font-weight: 600;
  transition: background var(--transition);
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>
