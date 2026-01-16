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
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag
              :type="getStatusType(row.status)"
              :effect="row.status === 'translating' ? 'dark' : 'light'"
            >
              <el-icon v-if="row.status === 'translating'" class="is-loading">
                <Loading />
              </el-icon>
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="150">
          <template #default="{ row }">
            <div class="progress-cell">
              <el-progress
                :percentage="row.progress"
                :status="row.status === 'completed' ? 'success' : undefined"
                :stroke-width="6"
              />
              <span class="progress-text">{{ row.progress }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" min-width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-cell">
              <div class="actions-full">
                <el-button
                  type="primary"
                  size="small"
                  :disabled="row.status !== 'completed'"
                  @click="downloadTask(row)"
                >
                  <el-icon><Download /></el-icon>
                  下载
                </el-button>
                <el-button
                  :type="row.status === 'completed' ? 'info' : 'warning'"
                  size="small"
                  @click="row.status === 'completed' ? showResultDetail(row) : refreshTaskRow(row)"
                >
                  <el-icon>
                    <template v-if="row.status === 'completed'"><Document /></template>
                    <template v-else><Refresh /></template>
                  </el-icon>
                  <span v-if="row.status === 'completed'">详情</span>
                  <span v-else>刷新</span>
                </el-button>
                <el-button type="danger" size="small" @click="deleteTask(row)">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </div>

              <div class="actions-icons">
                <el-button
                  type="primary"
                  size="small"
                  circle
                  :disabled="row.status !== 'completed'"
                  @click="downloadTask(row)"
                  aria-label="下载"
                >
                  <el-icon><Download /></el-icon>
                </el-button>
                <el-button
                  :type="row.status === 'completed' ? 'info' : 'warning'"
                  size="small"
                  circle
                  @click="row.status === 'completed' ? showResultDetail(row) : refreshTaskRow(row)"
                  :aria-label="row.status === 'completed' ? '详情' : '刷新'"
                >
                  <el-icon>
                    <template v-if="row.status === 'completed'"><Document /></template>
                    <template v-else><Refresh /></template>
                  </el-icon>
                </el-button>
                <el-button type="danger" size="small" circle @click="deleteTask(row)" aria-label="删除">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>

              <div class="actions-dropdown">
                <el-dropdown placement="bottom" trigger="click">
                  <el-button type="primary" size="small" circle aria-label="更多">
                    <el-icon><More /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item :disabled="row.status !== 'completed'" @click="downloadTask(row)">
                        <el-icon><Download /></el-icon>
                        下载
                      </el-dropdown-item>
                      <el-dropdown-item @click="showResultDetail(row)">
                        <el-icon><Document /></el-icon>
                        详情
                      </el-dropdown-item>
                      <el-dropdown-item v-if="row.status !== 'completed'" @click="refreshTaskRow(row)">
                        <el-icon><Refresh /></el-icon>
                        刷新
                      </el-dropdown-item>
                      <el-dropdown-item @click="deleteTask(row)">
                        <el-icon><Delete /></el-icon>
                        删除
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
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
    <el-dialog v-model="progressDialogVisible" title="翻译进度详情" width="400px">
      <div v-if="selectedTask" class="progress-detail">
        <div class="progress-info">
          <p><strong>文件名：</strong>{{ selectedTask.filename }}</p>
          <p>
            <strong>状态：</strong>
            <el-tag :type="getStatusType(selectedTask.status)">
              {{ getStatusLabel(selectedTask.status) }}
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
      <el-button
        type="primary"
        :disabled="selectedTask?.status !== 'completed'"
        @click="downloadSelectedTask"
      >
        下载结果
      </el-button>
    </span>
  </template>
</el-dialog>

 
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Loading, Refresh, Download, Delete, More } from '@element-plus/icons-vue'
import { useTranslationStore } from '@/stores/translation'
import { getTranslationList, downloadTranslation, getTranslationProgress } from '@/services/api'
import { getStatusLabel, getStatusType, downloadFile } from '@/utils'
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

// 下载任务
const downloadTask = async (task: TranslationTask) => {
  if (task.status !== 'completed') {
    ElMessage.warning('翻译未完成，无法下载')
    return
  }

  try {
    const blob: any = await downloadTranslation(task.taskId)
    const filename = task.filename.replace('.pdf', '_translated.pdf')
    downloadFile(blob, filename)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
    console.error('下载错误:', error)
  }
}

// 重试任务
const retryTask = (_task: TranslationTask) => {
  ElMessage.info('重试功能开发中...')
  // TODO: 实现重试逻辑
}

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

// 显示进度详情
const showProgressDetail = (task: TranslationTask) => {
  selectedTask.value = task
  progressDialogVisible.value = true
}

// 下载选中的任务
const downloadSelectedTask = () => {
  if (selectedTask.value) {
    downloadTask(selectedTask.value)
    progressDialogVisible.value = false
  }
}

// 自动刷新
let refreshInterval: number | null = null
const startAutoRefresh = () => {
  // 每3秒刷新一次
  refreshInterval = window.setInterval(() => {
    // 仅更新正在翻译的行，避免整表刷新与全局loading
    const translatingTasks = tasks.value.filter((task) => task.status === 'translating')
    if (translatingTasks.length > 0) {
      Promise.all(
        translatingTasks.map(async (task) => {
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
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-text {
  font-size: 12px;
  color: #909399;
  min-width: 35px;
}

.action-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.actions-full,
.actions-icons,
.actions-dropdown {
  display: none;
}

@media (min-width: 1024px) {
  .actions-full { display: flex; gap: 8px; }
}

@media (min-width: 768px) and (max-width: 1023px) {
  .actions-icons { display: flex; gap: 8px; }
}

@media (max-width: 767px) {
  .actions-dropdown { display: block; }
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
