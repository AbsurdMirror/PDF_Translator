<template>
  <div class="upload-container">
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span>PDF文件上传</span>
          <el-tag type="info">支持拖拽上传</el-tag>
        </div>
      </template>

      <!-- 上传区域 -->
      <div
        class="upload-area"
        :class="{ 'drag-over': isDragOver }"
        @drop="handleDrop"
        @dragover.prevent="isDragOver = true"
        @dragleave="isDragOver = false"
        @dragenter.prevent
      >
        <div v-if="!currentFile" class="upload-placeholder">
          <el-icon class="upload-icon" :size="48">
            <UploadFilled />
          </el-icon>
          <p class="upload-text">拖拽PDF文件到此处，或</p>
          <el-button type="primary" @click="selectFile"> 选择文件 </el-button>
          <p class="upload-hint">仅支持PDF格式，最大50MB</p>
        </div>

        <div v-else class="file-info">
          <el-icon class="file-icon" :size="32">
            <Document />
          </el-icon>
          <div class="file-details">
            <p class="file-name">{{ currentFile.name }}</p>
            <p class="file-size">{{ formatFileSize(currentFile.size) }}</p>
          </div>
          <el-button type="danger" size="small" circle @click="removeFile">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 语言选择 -->
      <div class="language-options" v-if="currentFile">
        <div class="lang-select-group">
          <span class="label">源语言</span>
          <el-select v-model="sourceLang" placeholder="请选择" style="width: 140px">
            <el-option
              v-for="item in languages"
              :key="item.value"
              :label="item.name"
              :value="item.value"
            />
          </el-select>
        </div>
        
        <el-icon class="arrow-icon"><Right /></el-icon>
        
        <div class="lang-select-group">
          <span class="label">目标语言</span>
          <el-select v-model="targetLang" placeholder="请选择" style="width: 140px">
            <el-option
              v-for="item in languages"
              :key="item.value"
              :label="item.name"
              :value="item.value"
            />
          </el-select>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <el-button
          type="primary"
          size="large"
          :disabled="!currentFile || isUploading"
          :loading="isUploading"
          @click="startTranslation"
        >
          {{ isUploading ? '解析中...' : '上传并解析' }}
        </el-button>
      </div>
    </el-card>

    <!-- 隐藏的文件输入 -->
    <input
      ref="fileInput"
      type="file"
      accept=".pdf"
      style="display: none"
      @change="handleFileSelect"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Document, Delete, Right } from '@element-plus/icons-vue'
import { useTranslationStore } from '@/stores/translation'
import { uploadFile, getLanguages } from '@/services/api'
import { formatFileSize } from '@/utils'
import { useRouter } from 'vue-router'

const translationStore = useTranslationStore()
const router = useRouter()

// 文件相关状态
const fileInput = ref<HTMLInputElement>()
const currentFile = ref<File | null>(null)
const isDragOver = ref(false)
const isUploading = ref(false)

// 语言相关状态
const languages = ref<{name: string, value: string}[]>([])
const sourceLang = ref('English')
const targetLang = ref('English')

onMounted(async () => {
  try {
    const res: any = await getLanguages()
    if (res.languages) {
      languages.value = res.languages
    }
  } catch (error) {
    console.error('获取语言列表失败', error)
  }
})


// 选择文件
const selectFile = () => {
  fileInput.value?.click()
}

// 处理文件选择
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    validateAndSetFile(file)
  }
}

// 处理拖拽文件
const handleDrop = (event: DragEvent) => {
  event.preventDefault()
  isDragOver.value = false

  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    const file = files[0]
    validateAndSetFile(file)
  }
}

// 验证并设置文件
const validateAndSetFile = (file: File) => {
  // 检查文件类型
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    ElMessage.error('请选择PDF格式的文件')
    return
  }

  // 检查文件大小（50MB限制）
  const maxSize = 50 * 1024 * 1024 // 50MB
  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过50MB')
    return
  }

  currentFile.value = file
}

// 移除文件
const removeFile = () => {
  currentFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// 开始翻译
const startTranslation = async () => {
  if (!currentFile.value) return

  isUploading.value = true

  try {
    // 上传文件
    const result: any = await uploadFile(currentFile.value, sourceLang.value, targetLang.value)

    // 添加任务到store
    const newTask = {
        taskId: result.taskId,
        filename: currentFile.value.name,
        status: result.status,
        parseProgress: 0,
        translateProgress: 0,
        createTime: new Date().toLocaleString(),
        message: '等待解析'
    }
    translationStore.addTask(newTask as any)

    ElMessage.success('文件上传成功，开始解析')

    // 跳转到翻译列表页面
    setTimeout(() => {
      router.push('/list')
    }, 1000)
  } catch (error) {
    ElMessage.error('上传失败，请重试')
    console.error('上传错误:', error)
  } finally {
    isUploading.value = false
  }
}
</script>

<style scoped>
.upload-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 20px;
}

.upload-card {
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
}

.upload-area {
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 60px 20px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
}

.upload-area:hover {
  border-color: #409eff;
}

.upload-area.drag-over {
  border-color: #409eff;
  background-color: #f0f9ff;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.upload-icon {
  color: #909399;
}

.upload-text {
  font-size: 16px;
  color: #606266;
  margin: 0;
}

.upload-hint {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.file-icon {
  color: #409eff;
}

.file-details {
  flex: 1;
  text-align: left;
}

.file-name {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin: 0 0 4px 0;
}

.file-size {
  font-size: 14px;
  color: #909399;
  margin: 0;
}


.language-options {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  padding: 0 20px;
}

.lang-select-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.lang-select-group .label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.arrow-icon {
  color: #909399;
  font-size: 20px;
}

.action-buttons {
  margin-top: 24px;
  display: flex;
  gap: 16px;
  justify-content: center;
}

@media (max-width: 768px) {
  .upload-container {
    padding: 20px 16px;
  }

  .upload-area {
    padding: 40px 16px;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
