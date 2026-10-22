<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)

router.beforeEach((to, from, next) => {
  loading.value = true
  next()
})
router.afterEach(() => {
  loading.value = false
})
</script>

<template>
  <div v-if="loading" class="route-progress">
    <div class="route-progress-bar" />
  </div>
  <router-view />
</template>

<style>
.route-progress { position: fixed; top: 0; left: 0; right: 0; height: 2px; z-index: 9999; }
.route-progress-bar {
  height: 100%; width: 55%; background: var(--color-primary);
  animation: route-slide 1.1s ease-in-out infinite;
}
@keyframes route-slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(190%); }
}
@media (prefers-reduced-motion: reduce) {
  .route-progress-bar { animation: none; width: 100%; opacity: .5; }
}
</style>
