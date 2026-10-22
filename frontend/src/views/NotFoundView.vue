<template>
  <div class="notfound">
    <div class="code num">404</div>
    <h2>页面不存在</h2>
    <p class="muted">你访问的地址可能已被移动或删除</p>
    <el-button type="primary" @click="$router.push('/dashboard')">返回概览</el-button>
  </div>
</template>

<style scoped>
.notfound { min-height: 70vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; }
.code { font-size: 96px; font-weight: 700; color: var(--color-primary); line-height: 1; opacity: .18; }
h2 { margin: 0; font-size: var(--font-20); }
p { margin: 0 0 8px; }
</style>
