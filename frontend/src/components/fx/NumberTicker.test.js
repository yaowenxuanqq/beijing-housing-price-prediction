import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import NumberTicker from './NumberTicker.vue'

describe('NumberTicker', () => {
  it('renders final value immediately when reduced motion is preferred', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }))
    const wrapper = mount(NumberTicker, { props: { value: 1234 } })
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('1,234')
  })
})
