<script setup>
defineProps({
  panel: {
    type: Object,
    required: true
  },
  position: {
    type: String,
    default: 'right'
  }
})

defineEmits(['close'])
</script>

<template>
  <aside class="plugin-panel" :class="position">
    <header class="plugin-panel-header">
      <div class="plugin-panel-title">
        <strong>{{ panel.title || panel.name || panel.id }}</strong>
        <span>{{ panel.pluginName }}</span>
      </div>
      <button class="plugin-panel-close" type="button" @click="$emit('close')" aria-label="Close plugin panel">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </header>

    <div class="plugin-panel-content">
      <component
        v-if="panel.component"
        :is="panel.component"
        :panel="panel"
      />
      <div v-else class="plugin-panel-empty">
        <p v-if="panel.description">{{ panel.description }}</p>
        <p v-else>{{ panel.pluginName }} registered this panel without a frontend component.</p>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.plugin-panel {
  width: 320px;
  min-width: 240px;
  max-width: 520px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  color: var(--text);
  flex-shrink: 0;
}

.plugin-panel.left {
  border-right: 1px solid var(--border);
}

.plugin-panel.right {
  border-left: 1px solid var(--border);
}

.plugin-panel-header {
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.plugin-panel-title {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.plugin-panel-title strong,
.plugin-panel-title span {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.plugin-panel-title strong {
  font-size: 13px;
  font-weight: 600;
}

.plugin-panel-title span {
  color: var(--subtext);
  font-size: 11px;
}

.plugin-panel-close {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--subtext);
  cursor: pointer;
  flex-shrink: 0;
}

.plugin-panel-close:hover {
  background: var(--overlay);
  color: var(--text);
}

.plugin-panel-content {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.plugin-panel-empty {
  padding: 16px;
  color: var(--subtext);
  font-size: 12px;
  line-height: 1.5;
}
</style>
