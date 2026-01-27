import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface TranslationTask {
  taskId: string
  filename: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  createTime: string
  message?: string
}

export interface TranslationConfig {
  aliyunAccessKeyId: string
  aliyunAccessKeySecret: string
  aliyunRegion: string
  aliyunEndpoint: string
  llmApiKey: string
  llmModel: string
  llmEndpoint: string
}

export const useTranslationStore = defineStore('translation', () => {
  // 翻译任务列表
  const tasks = ref<TranslationTask[]>([])

  // 当前翻译配置
  const config = ref<TranslationConfig>({
    aliyunAccessKeyId: '',
    aliyunAccessKeySecret: '',
    aliyunRegion: '',
    aliyunEndpoint: 'https://docmind-api.cn-hangzhou.aliyuncs.com',
    llmApiKey: '',
    llmModel: '',
    llmEndpoint: 'https://dashscope.aliyuncs.com/compatible-mode/v1'
  })

  // 添加翻译任务
  const addTask = (task: TranslationTask) => {
    tasks.value.unshift(task)
  }

  // 更新任务状态
  const updateTask = (taskId: string, updates: Partial<TranslationTask>) => {
    const task = tasks.value.find((t) => t.taskId === taskId)
    if (task) {
      Object.assign(task, updates)
    }
  }

  // 删除任务
  const removeTask = (taskId: string) => {
    const index = tasks.value.findIndex((t) => t.taskId === taskId)
    if (index > -1) {
      tasks.value.splice(index, 1)
    }
  }

  // 更新配置
  const updateConfig = (newConfig: Partial<TranslationConfig>) => {
    Object.assign(config.value, newConfig)
    // 保存到本地存储
    localStorage.setItem('translationConfig', JSON.stringify(config.value))
  }

  // 从本地存储加载配置
  const loadConfig = () => {
    const saved = localStorage.getItem('translationConfig')
    if (saved) {
      try {
        const savedConfig = JSON.parse(saved)
        Object.assign(config.value, savedConfig)
      } catch (error) {
        console.error('加载配置失败:', error)
      }
    }
  }

  // 初始化时加载配置
  loadConfig()

  return {
    tasks,
    config,
    addTask,
    updateTask,
    removeTask,
    updateConfig
  }
})
