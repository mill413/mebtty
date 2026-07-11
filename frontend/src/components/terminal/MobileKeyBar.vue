<script setup>
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
    <button
      v-for="item in keys"
      :key="item.key || item.modifier"
      type="button"
      class="mobile-key"
      :class="{ active: item.modifier && props.modifiers[item.modifier] }"
      :aria-label="item.ariaLabel || item.label"
      :aria-pressed="item.modifier ? props.modifiers[item.modifier] : undefined"
      @pointerdown.prevent="press(item)"
      @keydown.enter.space.prevent="press(item)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<style scoped>
.mobile-key-bar {
  display: none;
  align-items: center;
  gap: 5px;
  min-height: 42px;
  padding: 5px 7px calc(5px + env(safe-area-inset-bottom));
  overflow-x: auto;
  overscroll-behavior-x: contain;
  background: var(--bg-deep);
  border-top: 1px solid var(--border);
  scrollbar-width: none;
  touch-action: pan-x;
}

.mobile-key-bar::-webkit-scrollbar {
  display: none;
}

.mobile-key {
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

@media (hover: none), (pointer: coarse) {
  .mobile-key-bar {
    display: flex;
  }
}
</style>
