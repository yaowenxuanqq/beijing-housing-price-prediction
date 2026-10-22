import { describe, expect, it } from 'vitest'
import { useAsync } from './useAsync'

describe('useAsync', () => {
  it('stores successful data and clears loading', async () => {
    const { data, loading, error, run } = useAsync(async value => value * 2)
    await expect(run(5)).resolves.toBe(10)
    expect(data.value).toBe(10)
    expect(loading.value).toBe(false)
    expect(error.value).toBeNull()
  })

  it('captures rejection and clears loading', async () => {
    const failure = new Error('request failed')
    const { data, loading, error, run } = useAsync(async () => { throw failure })
    await expect(run()).rejects.toBe(failure)
    expect(data.value).toBeNull()
    expect(loading.value).toBe(false)
    expect(error.value).toBe(failure)
  })
})
