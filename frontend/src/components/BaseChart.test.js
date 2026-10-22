import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../utils/echartsTheme', () => ({
  default: {
    init: vi.fn(() => { throw new Error('init failed') })
  }
}))

import BaseChart from './BaseChart.vue'

describe('BaseChart', () => {
  it('renders a fallback when chart initialization fails', async () => {
    const wrapper = mount(BaseChart, { props: { option: { series: [] } } })
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('图表初始化失败')
  })
})
