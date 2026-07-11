<script setup>
import '@vscode/codicons/dist/codicon.css'

const props = defineProps({
  modifiers: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['key', 'modifier'])

const keys = [
  { key: 'escape', label: 'Esc' },
  { key: 'tab', label: 'Tab' },
  { modifier: 'ctrl', label: 'Ctrl' },
  { modifier: 'alt', label: 'Alt' },
  { modifier: 'shift', label: 'Shift' },
  { key: 'arrowLeft', label: '←', ariaLabel: 'Left arrow' },
  { key: 'arrowDown', label: '↓', ariaLabel: 'Down arrow' },
  { key: 'arrowUp', label: '↑', ariaLabel: 'Up arrow' },
  { key: 'arrowRight', label: '→', ariaLabel: 'Right arrow' },
  { key: 'home', label: 'Home' },
  { key: 'end', label: 'End' },
  { key: 'pageUp', label: 'PgUp' },
  { key: 'pageDown', label: 'PgDn' }
]

function press(item) {
  if (item.modifier) {
    emit('modifier', item.modifier)
  } else {
    emit('key', item.key)
  }
}
</script>

<template>
  <div class="mobile-key-bar" role="toolbar" aria-label="Terminal extra keys">
    <div class="mobile-key-scroll">
      <button
        v-for="item in keys"
        :key="item.key || item.modifier"
        type="button"
        tabindex="-1"
        class="mobile-key"
        :class="{ active: item.modifier && props.modifiers[item.modifier] }"
        :aria-label="item.ariaLabel || item.label"
        :aria-pressed="item.modifier ? props.modifiers[item.modifier] : undefined"
        @pointerdown.prevent="press(item)"
      >
        {{ item.label }}
      </button>
    </div>
    <button
      type="button"
      tabindex="-1"
      class="mobile-key mobile-keyboard-toggle"
      aria-label="Show keyboard"
      @pointerdown.prevent="$emit('key', 'keyboard')"
    >
      <i class="codicon codicon-keyboard" aria-hidden="true"></i>
    </button>
  </div>
</template>

<style scoped>
.mobile-key-bar {
  display: none;
  align-items: center;
  gap: 5px;
  min-height: 42px;
  padding: 5px 7px;
  overflow: hidden;
  background: var(--bg-deep);
  border-top: 1px solid var(--border);
}

.mobile-key-scroll {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 5px;
  min-width: 0;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  scrollbar-width: none;
  touch-action: pan-x;
}

.mobile-key-scroll::-webkit-scrollbar {
  display: none;
}

.mobile-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  min-width: 42px;
  height: 32px;
  padding: 0 9px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  user-select: none;
}

.mobile-key:active,
.mobile-key.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.mobile-keyboard-toggle {
  margin-left: 2px;
}

.mobile-keyboard-toggle .codicon {
  font-size: 18px;
}

@media (hover: none), (pointer: coarse) {
  .mobile-key-bar {
    display: flex;
  }
}
</style>
