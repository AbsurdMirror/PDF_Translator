<template>
  <div class="list-container">
    <el-card class="list-card">
      <template #header>
        <div class="card-header">
          <span>翻译历史记录</span>
          <div class="header-actions">
            <el-button type="primary" size="small" @click="refreshList">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button
              type="danger"
              size="small"
              :disabled="selectedTasks.length === 0"
              @click="batchDelete"
            >
              <el-icon><Delete /></el-icon>
              批量删除
            </el-button>
          </div>
        </div>
      </template>

      <!-- 任务列表 -->
      <el-table
        :data="tasks"
        style="width: 100%"
        @selection-change="handleSelectionChange"
        v-loading="loading"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="filename" label="文件名" min-width="200">
          <template #default="{ row }">
            <div class="filename-cell" @click="showResultDetail(row)" style="cursor: pointer;">
              <el-icon class="file-icon"><Document /></el-icon>
              <span class="filename-text">{{ row.filename }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="解析阶段" width="170">
          <template #default="{ row }">
            <div class="stage-cell">
              <el-tag
                :type="getParseStatusType(row.status)"
                :effect="row.status === 'processing' ? 'dark' : 'light'"
              >
                <el-icon v-if="row.status === 'processing'" class="is-loading">
                  <Loading />
                </el-icon>
                {{ getParseStatusLabel(row.status) }}
              </el-tag>
              <div class="progress-cell">
                <el-progress
                  :percentage="row.progress"
                  :status="row.status === 'completed' ? 'success' : (row.status === 'failed' ? 'exception' : undefined)"
                  :stroke-width="6"
                />
                <!-- <span class="progress-text">{{ row.progress }}%</span> -->
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="翻译阶段" width="170">
          <template #default>
            <div class="stage-cell">
              <el-tag type="info" effect="light">未开始</el-tag>
              <div class="progress-cell">
                <el-progress :percentage="0" :stroke-width="6" />
                <!-- <span class="progress-text">0%</span> -->
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-cell">
              <el-button type="primary" size="small" @click="refreshTaskRow(row)">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
              <el-button type="info" size="small" @click="showResultDetail(row)">
                <el-icon><Document /></el-icon>
                详情
              </el-button>
              <el-button type="danger" size="small" @click="deleteTask(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty
        v-if="!loading && tasks.length === 0"
        description="暂无翻译任务"
        class="empty-state"
      >
        <el-button type="primary" @click="$router.push('/')"> 上传PDF文件 </el-button>
      </el-empty>
    </el-card>

    <!-- 进度详情对话框 -->
    <el-dialog v-model="progressDialogVisible" title="解析进度详情" width="400px">
      <div v-if="selectedTask" class="progress-detail">
        <div class="progress-info">
          <p><strong>文件名：</strong>{{ selectedTask.filename }}</p>
          <p>
            <strong>状态：</strong>
            <el-tag :type="getParseStatusType(selectedTask.status)">
              {{ getParseStatusLabel(selectedTask.status) }}
            </el-tag>
          </p>
          <p><strong>进度：</strong>{{ selectedTask.progress }}%</p>
          <p v-if="selectedTask.message"><strong>详细信息：</strong>{{ selectedTask.message }}</p>
        </div>
        <el-progress
          :percentage="selectedTask.progress"
          :status="selectedTask.status === 'completed' ? 'success' : undefined"
          :stroke-width="10"
        />
      </div>
  <template #footer>
    <span class="dialog-footer">
      <el-button @click="progressDialogVisible = false">关闭</el-button>
    </span>
  </template>
</el-dialog>

 
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Loading, Refresh, Delete } from '@element-plus/icons-vue'
import { useTranslationStore } from '@/stores/translation'
import { getTranslationList, getTranslationProgress } from '@/services/api'
import type { TranslationTask } from '@/stores/translation'

const translationStore = useTranslationStore()
const router = useRouter()

// 状态管理
const loading = ref(false)
const selectedTasks = ref<TranslationTask[]>([])
const progressDialogVisible = ref(false)
const selectedTask = ref<TranslationTask | null>(null)
// 详情改为独立页面

// 计算属性
const tasks = computed(() => translationStore.tasks)

// 获取任务列表
const fetchTasks = async () => {
  loading.value = true
  try {
    const result: any = await getTranslationList()
    // 更新store中的任务列表
    if (result && result.tasks) {
      result.tasks.forEach((task: TranslationTask) => {
        const existingTask = translationStore.tasks.find((t) => t.taskId === task.taskId)
        if (existingTask) {
          translationStore.updateTask(task.taskId, task)
        } else {
          translationStore.addTask(task)
        }
      })
    }
  } catch (error) {
    ElMessage.error('获取任务列表失败')
    console.error('获取任务列表错误:', error)
  } finally {
    loading.value = false
  }
}

// 刷新列表
const refreshList = () => {
  fetchTasks()
}

const refreshTaskRow = async (task: TranslationTask) => {
  try {
    const result: any = await getTranslationProgress(task.taskId)
    const { progress, status, message } = result
    translationStore.updateTask(task.taskId, { progress, status, message })
  } catch (error) {
    ElMessage.error('刷新失败')
  }
}

const showResultDetail = async (task: TranslationTask) => {
  router.push(`/detail/${task.taskId}`)
}

// 处理选择变化
const handleSelectionChange = (selection: TranslationTask[]) => {
  selectedTasks.value = selection
}

// 重试任务
// 删除任务
const deleteTask = async (task: TranslationTask) => {
  try {
    await ElMessageBox.confirm(`确定要删除任务 "${task.filename}" 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    translationStore.removeTask(task.taskId)
    ElMessage.success('删除成功')
  } catch (error) {
    // 用户取消删除
  }
}

// 批量删除
const batchDelete = async () => {
  if (selectedTasks.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedTasks.value.length} 个任务吗？`,
      '确认批量删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    selectedTasks.value.forEach((task) => {
      translationStore.removeTask(task.taskId)
    })

    ElMessage.success('批量删除成功')
  } catch (error) {
    // 用户取消删除
  }
}

// 自动刷新
let refreshInterval: number | null = null
const startAutoRefresh = () => {
  // 每3秒刷新一次
  refreshInterval = window.setInterval(() => {
    // 仅更新正在翻译的行，避免整表刷新与全局loading
    const processingTasks = tasks.value.filter((task) => task.status === 'processing')
    if (processingTasks.length > 0) {
      Promise.all(
        processingTasks.map(async (task) => {
          try {
            const response: any = await getTranslationProgress(task.taskId)
            const { progress, status, message } = response
            translationStore.updateTask(task.taskId, { progress, status, message })
          } catch (e) {
            // 行级更新失败时忽略，避免打断其他行更新
          }
        })
      )
    }
  }, 3000)
}

const getParseStatusLabel = (status: string): string => {
  const statusMap: Record<string, string> = {
    pending: '待解析',
    processing: '解析中',
    completed: '解析完成',
    failed: '解析失败'
  }
  return statusMap[status] || status
}

const getParseStatusType = (status: string): string => {
  const typeMap: Record<string, string> = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

const stopAutoRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

// 生命周期
onMounted(() => {
  fetchTasks()
  startAutoRefresh()
})

// 组件卸载时停止自动刷新
import { onUnmounted } from 'vue'
onUnmounted(() => {
  stopAutoRefresh()
})

 
</script>

<style scoped>
.list-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.list-card {
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

.header-actions {
  display: flex;
  gap: 12px;
}

.filename-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon {
  color: #409eff;
}

.filename-text {
  font-weight: 500;
  color: #303133;
}

.progress-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.progress-cell :deep(.el-progress) {
  width: 120px;
  flex: 0 0 120px;
}

.progress-text {
  font-size: 12px;
  color: #909399;
  min-width: 28px;
}

.stage-cell {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.stage-cell :deep(.el-tag) {
  padding: 0 6px;
  height: 22px;
  line-height: 20px;
  font-size: 12px;
  max-width: 100%;
  white-space: nowrap;
}

.action-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.empty-state {
  padding: 60px 0;
}

.progress-detail {
  padding: 20px 0;
}

.progress-info {
  margin-bottom: 20px;
}

.progress-info p {
  margin: 8px 0;
  font-size: 14px;
}

.markdown-body {
  font-size: 14px;
  line-height: 1.8;
}
.markdown-body h1,
.markdown-body h2,
.markdown-body h3 {
  margin: 12px 0;
}
.markdown-body pre {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  overflow: auto;
}
.markdown-body code {
  background: #f0f0f0;
  padding: 2px 4px;
  border-radius: 4px;
}

.is-loading {
  animation: rotating 1s linear infinite;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 768px) {
  .list-container {
    padding: 16px;
  }

  .card-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
