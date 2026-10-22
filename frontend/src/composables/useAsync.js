import { ref } from 'vue'

/**
 * 统一异步加载状态：data / loading / error / run
 * 用法：const { data, loading, error, run } = useAsync(fetchFn)
 */
export function useAsync(fn) {
  const data = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function run(...args) {
    loading.value = true
    error.value = null
    try {
      data.value = await fn(...args)
      return data.value
    } catch (err) {
      error.value = err
      throw err
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, run }
}
