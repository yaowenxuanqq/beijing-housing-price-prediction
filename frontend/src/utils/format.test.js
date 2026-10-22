import { describe, expect, it } from 'vitest'
import { fmtNumber, fmtPct, fmtR2, fmtWan } from './format'

describe('format utils', () => {
  it('formats thousands separator', () => {
    expect(fmtNumber(317718)).toBe('317,718')
  })
  it('returns dash for null', () => {
    expect(fmtNumber(null)).toBe('-')
  })
  it('formats wan with one decimal', () => {
    expect(fmtWan(349.55)).toBe('349.6 万')
  })
  it('formats percent', () => {
    expect(fmtPct(12.345)).toBe('12.35%')
  })
  it('formats r2', () => {
    expect(fmtR2(0.86624)).toBe('0.8662')
  })
})
