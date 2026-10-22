import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PageHeader from './PageHeader.vue'

describe('PageHeader', () => {
  it('renders title, description and action slot', () => {
    const wrapper = mount(PageHeader, {
      props: {
        title: '模型对比',
        description: '统一指标口径',
        eyebrow: 'Models'
      },
      slots: { actions: '<button>刷新</button>' }
    })
    expect(wrapper.text()).toContain('模型对比')
    expect(wrapper.text()).toContain('统一指标口径')
    expect(wrapper.text()).toContain('Models')
    expect(wrapper.find('.actions button').text()).toBe('刷新')
  })
})
