import axios from 'axios'
import { ElMessage } from 'element-plus'

export const client = axios.create({
  baseURL: '/api/v1',
  timeout: 60000
})

client.interceptors.response.use(
  response => response,
  error => {
    const data = error.response?.data
    let msg = data?.error || error.message
    if (!msg && data?.errors) {
      msg = Object.entries(data.errors)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join('；')
    }
    if (error.response?.status === 503) msg = '模型未就绪，请先运行 scripts/04_tune.py'
    ElMessage.error(msg || '请求失败')
    return Promise.reject(error)
  }
)
