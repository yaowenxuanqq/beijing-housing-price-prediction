import * as echarts from 'echarts'

export function registerEchartsTheme() {
  echarts.registerTheme('housing', {
    color: ['#2f6fed', '#13c2c2', '#faad14', '#f5222d', '#8172b3', '#55a868'],
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif', color: '#303133' },
    title: { textStyle: { fontSize: 14, fontWeight: 600, color: '#303133' } },
    legend: { textStyle: { color: '#606266', fontSize: 12 } },
    tooltip: {
      backgroundColor: 'rgba(255,255,255,.96)',
      borderColor: '#e4e7ed',
      borderWidth: 1,
      textStyle: { color: '#303133', fontSize: 12 },
      extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,.12); border-radius: 6px;'
    },
    categoryAxis: {
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisTick: { show: false },
      axisLabel: { color: '#606266', fontSize: 11 },
      splitLine: { show: false }
    },
    valueAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#606266', fontSize: 11 },
      splitLine: { lineStyle: { color: '#ebeef5', type: 'dashed' } }
    }
  })
}
