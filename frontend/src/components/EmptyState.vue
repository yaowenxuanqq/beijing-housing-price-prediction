<script setup>
defineProps({ text: { type: String, default: '暂无数据' } })
</script>

<template>
  <div class="empty">
    <div class="empty-icon">◌</div>
    <div class="empty-text">{{ text }}</div>
  </div>
</template>

<style scoped>
.empty { min-height: 180px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: #a8abb2; }
.empty-icon { font-size: 34px; }
.empty-text { font-size: 13px; }
</style>
