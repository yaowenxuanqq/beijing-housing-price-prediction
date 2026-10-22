import { defineStore } from 'pinia'
import { fetchMetaOptions } from '../api/endpoints'

export const useAppStore = defineStore('app', {
  state: () => ({
    meta: null,
    metaLoaded: false,
    modelVersion: 'tuned_rf_es3_v2'
  }),
  actions: {
    async loadMeta(force = false) {
      if (this.metaLoaded && !force) return this.meta
      this.meta = await fetchMetaOptions()
      this.metaLoaded = true
      return this.meta
    }
  }
})
