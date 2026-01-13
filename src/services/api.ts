import axios from 'axios'

const API_BASE_URL = 'http://localhost:3002/api'

// 创建axios实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API请求失败:', error)
    return Promise.reject(error)
  }
)

// 文件上传
export const uploadFile = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)

  return api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 获取翻译进度
export const getTranslationProgress = (taskId: string) => {
  return api.get(`/progress/${taskId}`)
}

// 获取翻译列表
export const getTranslationList = () => {
  return api.get('/translations')
}

// 下载翻译结果
export const downloadTranslation = (taskId: string) => {
  return api.get(`/download/${taskId}`, {
    responseType: 'blob'
  })
}

// 获取配置
export const getConfig = () => {
  return api.get('/config')
}

// 保存配置
export const saveConfig = (config: any) => {
  return api.post('/config', config)
}

export default api
