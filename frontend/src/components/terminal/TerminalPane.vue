<script setup>
import { ref, watch, onMounted, onUnmounted, onActivated } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import { SearchAddon } from 'xterm-addon-search'
import { WebLinksAddon } from 'xterm-addon-web-links'
import 'xterm/css/xterm.css'
import { TerminalWebSocket } from '../../services/terminal-ws.js'
import { useThemeStore } from '../../stores/theme'

const props = defineProps({
  sessionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['resize', 'connection-change'])

const themeStore = useThemeStore()
const terminalEl = ref(null)
let terminal = null
let fitAddon = null
let searchAddon = null
let wsConnection = null
let resizeObserver = null
let copyOnSelectHandler = null

function legacyCopy(text) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.top = '0'
  textarea.style.left = '0'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()
  try {
    document.execCommand('copy')
  } catch {}
  document.body.removeChild(textarea)
}

const terminalThemes = {
  dark: {
    background: '#1e1e2e',
    foreground: '#cdd6f4',
    cursor: '#f5e0dc',
    cursorAccent: '#1e1e2e',
    selectionBackground: '#585b7066',
    selectionForeground: '#cdd6f4',
    black: '#45475a',
    red: '#f38ba8',
    green: '#a6e3a1',
    yellow: '#f9e2af',
    blue: '#89b4fa',
    magenta: '#f5c2e7',
    cyan: '#94e2d5',
    white: '#bac2de',
    brightBlack: '#585b70',
    brightRed: '#f38ba8',
    brightGreen: '#a6e3a1',
    brightYellow: '#f9e2af',
    brightBlue: '#89b4fa',
    brightMagenta: '#f5c2e7',
    brightCyan: '#94e2d5',
    brightWhite: '#a6adc8'
  },
  light: {
    background: '#eff1f5',
    foreground: '#4c4f69',
    cursor: '#dc8a78',
    cursorAccent: '#eff1f5',
    selectionBackground: '#9ca0b066',
    selectionForeground: '#4c4f69',
    black: '#5c5f77',
    red: '#d20f39',
    green: '#40a02b',
    yellow: '#df8e1d',
    blue: '#1e66f5',
    magenta: '#ea76cb',
    cyan: '#179299',
    white: '#acb0be',
    brightBlack: '#6c6f85',
    brightRed: '#d20f39',
    brightGreen: '#40a02b',
    brightYellow: '#df8e1d',
    brightBlue: '#1e66f5',
    brightMagenta: '#ea76cb',
    brightCyan: '#179299',
    brightWhite: '#bcc0cc'
  }
}

watch(() => themeStore.resolved, (newTheme) => {
  if (terminal) {
    terminal.options.theme = terminalThemes[newTheme]
  }
})

onMounted(() => {
  initTerminal()
})

onUnmounted(() => {
  cleanup()
})

onActivated(() => {
  // Re-fit and re-focus the terminal when the tab becomes active again
  if (terminal) {
    requestAnimationFrame(() => {
      try {
        fitAddon.fit()
        emit('resize', { cols: terminal.cols, rows: terminal.rows })
        if (wsConnection) {
          wsConnection.sendResize(terminal.cols, terminal.rows)
        }
      } catch {
        // Ignore fit errors on reactivation
      }
      terminal.focus()
    })
  }
})

async function initTerminal() {
  if (document.fonts?.load) {
    await Promise.all([
      document.fonts.load("14px 'MebTTY Mono'"),
      document.fonts.load("700 14px 'MebTTY Mono'")
    ]).catch(() => {})
  }

  if (!terminalEl.value) return

  terminal = new Terminal({
    cursorBlink: true,
    cursorStyle: 'bar',
    cursorWidth: 2,
    scrollback: 5000,
    fontSize: 14,
    fontFamily: "'MebTTY Mono', 'JetBrainsMonoNL Nerd Font', 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, monospace",
    lineHeight: 1.3,
    allowProposedApi: true,
    theme: terminalThemes[themeStore.resolved]
  })

  fitAddon = new FitAddon()
  searchAddon = new SearchAddon()

  terminal.loadAddon(fitAddon)
  terminal.loadAddon(searchAddon)
  terminal.loadAddon(new WebLinksAddon())

  terminal.open(terminalEl.value)

  // Handle Ctrl+V / Cmd+V paste (without Shift) since xterm.js only handles Ctrl+Shift+V by default
  terminal.attachCustomKeyEventHandler((e) => {
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && (e.key === 'v' || e.key === 'V' || e.code === 'KeyV')) {
      if (navigator.clipboard) {
        navigator.clipboard.readText().then((text) => {
          if (text && wsConnection) {
            wsConnection.sendData(text)
          }
        }).catch(() => {
          // Clipboard read may fail in insecure contexts; silently ignore
        })
      }
      return false
    }
    return true
  })

  // Copy-on-select: copy selected text to clipboard when user finishes a selection
  copyOnSelectHandler = () => {
    const selection = terminal.getSelection()
    if (!selection) return

    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(selection).catch(() => {
        // Fall through to legacy method
        legacyCopy(selection)
      })
    } else {
      // Fallback for insecure contexts (e.g. via HTTP tunnel) or older browsers
      legacyCopy(selection)
    }
  }
  terminalEl.value.addEventListener('mouseup', copyOnSelectHandler)
  terminalEl.value.addEventListener('keyup', (e) => {
    if (e.shiftKey) copyOnSelectHandler()
  })

  // Initial fit
  requestAnimationFrame(() => {
    fitAddon.fit()
    emit('resize', { cols: terminal.cols, rows: terminal.rows })
  })

  // Setup resize observer
  resizeObserver = new ResizeObserver(() => {
    if (fitAddon) {
      requestAnimationFrame(() => {
        try {
          fitAddon.fit()
          emit('resize', { cols: terminal.cols, rows: terminal.rows })
          if (wsConnection) {
            wsConnection.sendResize(terminal.cols, terminal.rows)
          }
        } catch {
          // Ignore fit errors during cleanup
        }
      })
    }
  })
  resizeObserver.observe(terminalEl.value)

  // Connect WebSocket
  wsConnection = new TerminalWebSocket(props.sessionId, terminal, {
    onConnect: () => {
      emit('connection-change', 'connected')
      wsConnection.sendResize(terminal.cols, terminal.rows)
    },
    onDisconnect: () => {
      emit('connection-change', 'disconnected')
    }
  })
  wsConnection.connect()

  terminal.focus()
}

function cleanup() {
  if (copyOnSelectHandler && terminalEl.value) {
    terminalEl.value.removeEventListener('mouseup', copyOnSelectHandler)
    copyOnSelectHandler = null
  }
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (wsConnection) {
    wsConnection.disconnect()
    wsConnection = null
  }
  if (terminal) {
    terminal.dispose()
    terminal = null
  }
}

function focus() {
  terminal?.focus()
}

function fit() {
  if (fitAddon) {
    fitAddon.fit()
    emit('resize', { cols: terminal.cols, rows: terminal.rows })
  }
}

function getTerminal() {
  return terminal
}

function openSearch() {
  // SearchAddon doesn't have a built-in UI in v0.13
  // We'll just focus the terminal for now
  terminal?.focus()
}

function closeSearch() {
  terminal?.focus()
}

defineExpose({ focus, fit, getTerminal, openSearch, closeSearch })
</script>

<template>
  <div class="terminal-pane">
    <div ref="terminalEl" class="terminal-container"></div>
  </div>
</template>

<style scoped>
.terminal-pane {
  width: 100%;
  height: 100%;
  padding: 0;
  background: var(--bg);
}

.terminal-container {
  width: 100%;
  height: 100%;
}

.terminal-container :deep(.xterm) {
  height: 100%;
}

.terminal-container :deep(.xterm-viewport) {
  overflow-y: auto;
}
</style>
