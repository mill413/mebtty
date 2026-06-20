<script setup>
defineProps({
  section: {
    type: Object,
    required: true
  }
})
</script>

<template>
  <div class="plugin-settings-section">
    <div class="plugin-settings-head">
      <div>
        <h4>{{ section.title || section.name || section.id }}</h4>
        <span>{{ section.pluginName }}</span>
      </div>
    </div>

    <component
      v-if="section.component"
      :is="section.component"
      :section="section"
    />
    <p v-else-if="section.description" class="plugin-settings-description">
      {{ section.description }}
    </p>
  </div>
</template>

<style scoped>
.plugin-settings-section {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  background: var(--bg);
}

.plugin-settings-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.plugin-settings-head h4 {
  margin: 0;
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
}

.plugin-settings-head span {
  display: block;
  margin-top: 3px;
  color: var(--subtext);
  font-size: 12px;
}

.plugin-settings-description {
  margin: 10px 0 0;
  color: var(--subtext);
  font-size: 13px;
  line-height: 1.5;
}
</style>
