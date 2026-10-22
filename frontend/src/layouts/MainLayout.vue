<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../stores/app'

const route = useRoute()
const store = useAppStore()

const groups = [
  {
    title: '数据分析',
    items: [
      { path: '/dashboard', label: '概览大屏', icon: '◫' },
      { path: '/houses', label: '数据管理', icon: '▤' },
      { path: '/analysis', label: '可视化分析', icon: '◔' }
    ]
  },
  {
    title: '模型应用',
    items: [
      { path: '/models', label: '模型对比', icon: '◎' },
      { path: '/predict', label: '房价预测', icon: '✦' }
    ]
  }
]

const pageTitle = computed(() => route.meta.title || '')
function refresh() { window.location.reload() }
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <div class="logo">BJ</div>
        <div class="brand-text">
          <b>北京二手房</b>
          <small>房价分析与预测</small>
        </div>
      </div>

      <nav class="nav">
        <template v-for="group in groups" :key="group.title">
          <div class="nav-group">{{ group.title }}</div>
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            active-class="active"
          >
            <span class="nav-icon">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </router-link>
        </template>
      </nav>

      <div class="sidebar-footer">
        <div>数据区间 2011 – 2017</div>
        <div>317,718 条成交记录</div>
        <div class="sidebar-version">System v1.6 · Model v2</div>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="topbar-left">
          <span class="crumb-root">北京二手房</span>
          <span class="crumb-separator">/</span>
          <span class="topbar-title">{{ pageTitle }}</span>
        </div>
        <div class="topbar-right">
          <span class="context-pill">北京 · 2011–2017</span>
          <el-tag size="small" type="success" effect="plain">模型 {{ store.modelVersion }}</el-tag>
          <span class="muted model-note">随机森林 · ratio 口径</span>
          <el-button size="small" plain @click="refresh">刷新页面</el-button>
        </div>
      </header>
      <main class="content">
        <router-view v-slot="{ Component, route: currentRoute }">
          <transition name="page" mode="out-in">
            <component :is="Component" :key="currentRoute.path" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout { display: flex; height: 100vh; overflow: hidden; }
.sidebar {
  width: 220px; flex: 0 0 220px; background: var(--bg-sidebar);
  display: flex; flex-direction: column; color: #c0c4cc;
}
.brand { display: flex; align-items: center; gap: 10px; padding: 20px 18px 18px; }
.logo {
  width: 38px; height: 38px; border-radius: 11px;
  background: linear-gradient(145deg, #4f83ff 0%, var(--color-primary) 55%, #2457c8 100%);
  box-shadow: 0 7px 18px rgba(47, 111, 237, .30);
  color: #fff; font-weight: 700; display: flex; align-items: center; justify-content: center;
  letter-spacing: -.04em;
}
.brand-text { display: flex; flex-direction: column; line-height: 1.3; }
.brand-text b { color: #fff; font-size: 15px; }
.brand-text small { color: #8a94a6; font-size: 11px; }
.nav { padding: 8px 10px; display: flex; flex-direction: column; gap: 3px; }
.nav-group {
  padding: 14px 14px 6px; font-size: 11px; letter-spacing: 1px;
  color: #6b7688;
}
.nav-item {
  position: relative;
  display: flex; align-items: center; gap: 10px; padding: 10px 14px;
  color: #c0c4cc; text-decoration: none; border-radius: 8px; font-size: 14px;
  transition: background .2s, color .2s;
}
.nav-item:hover { background: rgba(255,255,255,.06); color: #fff; }
.nav-item.active { background: var(--color-primary); color: #fff; }
.nav-item.active::before {
  content: ''; position: absolute; left: -10px; top: 9px; bottom: 9px; width: 3px;
  border-radius: 2px; background: #8fb0ff;
}
.nav-icon { width: 16px; text-align: center; opacity: .9; }
.sidebar-footer {
  margin-top: auto; padding: 16px 18px; font-size: 11px; line-height: 1.8;
  color: #758196; border-top: 1px solid rgba(255,255,255,.06);
}
.sidebar-version { margin-top: 5px; color: #586579; }
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.topbar {
  height: 58px; flex: 0 0 58px; background: rgba(255,255,255,.9);
  backdrop-filter: blur(14px); border-bottom: 1px solid var(--border-subtle);
  display: flex; align-items: center; justify-content: space-between; padding: 0 24px;
  position: relative; z-index: 20;
}
.topbar-left { display: flex; align-items: center; gap: 8px; min-width: 0; }
.crumb-root { color: var(--text-muted); font-size: var(--font-13); }
.crumb-separator { color: #c5cad3; font-size: 12px; }
.topbar-title { font-size: var(--font-14); font-weight: 650; }
.topbar-right { display: flex; align-items: center; gap: 10px; }
.context-pill {
  padding: 4px 9px; border-radius: 999px; background: var(--bg-page);
  color: var(--text-secondary); font-size: 11px; border: 1px solid var(--border-subtle);
}
.content { flex: 1; overflow: auto; scroll-behavior: smooth; }
.page-enter-active, .page-leave-active { transition: opacity .22s ease, transform .22s ease; }
.page-enter-from { opacity: 0; transform: translateY(7px); }
.page-leave-to { opacity: 0; transform: translateY(-4px); }

@media (max-width: 1180px) {
  .model-note, .context-pill { display: none; }
}
@media (max-width: 1024px) {
  .sidebar { width: 64px; flex-basis: 64px; }
  .brand-text, .nav-item span:last-child, .nav-group, .sidebar-footer { display: none; }
  .brand { justify-content: center; padding: 16px 0; }
  .nav-item { justify-content: center; padding: 12px 0; }
  .topbar { padding: 0 16px; }
}
@media (max-width: 640px) {
  .crumb-root, .crumb-separator, .topbar-right .muted { display: none; }
  .topbar-right { gap: 6px; }
}
@media (prefers-reduced-motion: reduce) {
  .page-enter-active, .page-leave-active { transition: none; }
}
</style>
