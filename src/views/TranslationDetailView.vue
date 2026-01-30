<template>
  <div class="detail-container">
    <el-card class="detail-card">
      <template #header>
        <div class="card-header">
          <div class="title-group">
            <el-icon class="file-icon"><Document /></el-icon>
            <span class="title-text">任务详情</span>
          </div>
          <div class="header-actions">
            <el-button size="small" @click="$router.back()">
              返回
            </el-button>
            <el-dropdown trigger="hover" placement="bottom-end">
              <el-button type="primary" size="small">
                <el-icon><Download /></el-icon>
                下载
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="downloadOriginalPdf">原始PDF</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button type="success" size="small" @click="startTranslate" :loading="translateSubmitting" :disabled="translateSubmitting">
              翻译
            </el-button>
            <el-dropdown trigger="hover" placement="bottom-end">
              <el-button size="small">
                查看
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="setViewMode('parse')">解析结果</el-dropdown-item>
                  <el-dropdown-item @click="setViewMode('translation')">翻译结果</el-dropdown-item>
                  <el-dropdown-item @click="setViewMode('compare')">解析-翻译对照</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </template>

      <div v-if="loading" class="loading-area">
        <el-skeleton :rows="6" animated />
      </div>
      <div v-else>
        <div class="meta-bar">
          <div class="meta">
            <p><strong>文件名：</strong>{{ task?.filename }}</p>
            <p><strong>任务ID：</strong>{{ taskId }}</p>
            <p><strong>创建时间：</strong>{{ task?.createTime }}</p>
            <p><strong>状态信息：</strong>{{ task?.message || '-' }}</p>
          </div>
          <div class="progress-rings">
            <div class="ring-item">
              <div class="ring-wrapper">
                <el-progress
                  type="circle"
                  :percentage="parseProgress"
                  :width="72"
                  :show-text="false"
                  :status="parseStatus"
                />
                <div class="ring-content">
                  <el-icon v-if="parseInnerMode === 'success'" class="ring-icon-success">
                    <Check />
                  </el-icon>
                  <el-icon v-else-if="parseInnerMode === 'exception'" class="ring-icon-exception">
                    <Close />
                  </el-icon>
                  <span v-else class="ring-text">{{ parseProgress }}%</span>
                </div>
              </div>
              <div class="ring-label">解析进度</div>
            </div>
            <div class="ring-item">
              <div class="ring-wrapper">
                <el-progress
                  type="circle"
                  :percentage="translationProgress"
                  :width="72"
                  :show-text="false"
                  :status="translationStatus"
                />
                <div class="ring-content">
                  <el-icon v-if="translationInnerMode === 'success'" class="ring-icon-success">
                    <Check />
                  </el-icon>
                  <el-icon v-else-if="translationInnerMode === 'exception'" class="ring-icon-exception">
                    <Close />
                  </el-icon>
                  <span v-else class="ring-text">{{ translationProgress }}%</span>
                </div>
              </div>
              <div class="ring-label">翻译进度</div>
            </div>
          </div>
        </div>
        
        <!-- 解析结果表格 -->
        <el-table v-if="viewMode === 'parse'" :data="parseResults" style="width: 100%" border stripe>
          <el-table-column prop="pageNum" label="页码" width="80" align="center" />
          <el-table-column prop="type" label="类型" width="100" align="center" />
          <el-table-column prop="subType" label="子类型" width="120" align="center">
             <template #default="{ row }">
               {{ row.subType || '-' }}
             </template>
          </el-table-column>
          <el-table-column prop="markdownContent" label="内容 (Markdown)">
            <template #default="{ row }">
              <div v-if="editingIndex === row.index">
                <el-input
                  v-model="editingContent"
                  type="textarea"
                  :autosize="{ minRows: 4, maxRows: 15 }"
                  placeholder="请输入 Markdown 内容"
                />
              </div>
              <div v-else class="markdown-preview markdown-body" v-html="renderMarkdown(row.markdownContent)"></div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" align="center" fixed="right">
            <template #default="{ row }">
              <div v-if="editingIndex === row.index" class="edit-actions">
                <el-button 
                  type="success" 
                  size="small" 
                  @click="saveEdit(row)" 
                  :loading="saving"
                  :disabled="saving"
                >
                  保存
                </el-button>
                <el-button 
                  size="small" 
                  @click="cancelEdit" 
                  :disabled="saving"
                >
                  取消
                </el-button>
              </div>
              <div v-else class="normal-actions">
                <el-button type="primary" size="small" @click="startEdit(row)">编辑</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-else-if="viewMode === 'translation'"
          description="暂无翻译结果"
          class="result-empty"
        />

        <el-empty
          v-else
          description="暂无对照结果"
          class="result-empty"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document, Download, Check, Close } from '@element-plus/icons-vue'
import { useTranslationStore } from '@/stores/translation'
import { getTaskDetail, downloadSourceFile, updateTaskResult, getTranslationProgress, submitTranslationTask } from '@/services/api'
import { downloadFile } from '@/utils'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import hljs from 'highlight.js'
import 'github-markdown-css/github-markdown.css'
import 'highlight.js/styles/github.css'

const route = useRoute()
const translationStore = useTranslationStore()

const taskId = route.params.taskId as string
const loading = ref(true)
const parseResults = ref<any[]>([])
const task = computed(() => translationStore.tasks.find((t) => t.taskId === taskId))
const editingIndex = ref<number | null>(null)
const editingContent = ref('')
const saving = ref(false)
const viewMode = ref<'parse' | 'translation' | 'compare'>('parse')
const translateSubmitting = ref(false)
const pollingTimer = ref<number | null>(null)

const parseProgress = computed(() => {
  return Math.max(0, Math.min(100, task.value?.parseProgress ?? 0))
})

const parseStatus = computed(() => {
  if (!task.value) return undefined
  if (parseProgress.value === 100) return 'success'
  if (task.value.status === 'failed' && parseProgress.value < 100) return 'exception'
  return undefined
})

const parseInnerMode = computed(() => {
  if (parseStatus.value === 'success') return 'success'
  if (parseStatus.value === 'exception') return 'exception'
  return 'percent'
})

const translationProgress = computed(() => {
  return Math.max(0, Math.min(100, task.value?.translateProgress ?? 0))
})

const translationStatus = computed(() => {
  if (!task.value) return undefined
  if (translationProgress.value === 100) return 'success'
  if (task.value.status === 'failed' && translationProgress.value < 100 && parseProgress.value === 100) return 'exception'
  return undefined
})
const translationInnerMode = computed(() => {
  if (translationStatus.value === 'success') return 'success'
  if (translationStatus.value === 'exception') return 'exception'
  return 'percent'
})

marked.use({
  extensions: [{
    name: 'math',
    level: 'inline',
    start(src: string) { return src.match(/\$/)?.index },
    tokenizer(src: string) {
      const blockRule = /^\$\$([\s\S]+?)\$\$/
      const inlineRule = /^\$([^$\n]+?)\$/
      
      let match = blockRule.exec(src)
      if (match) {
        return {
          type: 'math',
          raw: match[0],
          text: match[1].trim(),
          displayMode: true
        }
      }
      
      match = inlineRule.exec(src)
      if (match) {
        return {
          type: 'math',
          raw: match[0],
          text: match[1].trim(),
          displayMode: false
        }
      }
    },
    renderer(token: any) {
      return katex.renderToString(token.text, {
        displayMode: token.displayMode,
        throwOnError: false
      })
    }
  }],
  renderer: {
    code(token: any) {
      const rawCode: string = typeof token === 'string' ? token : (token?.text ?? '')
      const lang: string = (token?.lang ?? '').trim().split(/\s+/)[0]
      try {
        const highlighted = lang && hljs.getLanguage(lang)
          ? hljs.highlight(rawCode, { language: lang, ignoreIllegals: true }).value
          : hljs.highlightAuto(rawCode).value
        const langClass = lang ? ` language-${lang}` : ''
        return `<pre><code class="hljs${langClass}">${highlighted}</code></pre>`
      } catch {
        const escapeMap: Record<string, string> = {
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          "'": '&#39;'
        }
        const escaped = rawCode.replace(/[&<>"']/g, (ch) => escapeMap[ch] || ch)
        const langClass = lang ? ` language-${lang}` : ''
        return `<pre><code class="hljs${langClass}">${escaped}</code></pre>`
      }
    }
  }
})

const renderMarkdown = (content: string) => {
  if (!content) return ''
  // 预处理：将 \[ ... \] 转换为 $$ ... $$，将 \( ... \) 转换为 $ ... $
  let processedContent = content
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, p1) => `$$${p1}$$`)
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, p1) => `$${p1}$`)

  const html = marked.parse(processedContent, { async: false }) as string
  return DOMPurify.sanitize(html)
}

const startEdit = (row: any) => {
  editingIndex.value = row.index
  editingContent.value = row.markdownContent
}

const cancelEdit = () => {
  editingIndex.value = null
  editingContent.value = ''
}

const saveEdit = async (row: any) => {
  saving.value = true
  try {
    await updateTaskResult(taskId, row.index, editingContent.value)
    row.markdownContent = editingContent.value
    ElMessage.success('保存成功')
    editingIndex.value = null
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const fetchDetail = async () => {
  loading.value = true
  try {
    const res: any = await getTaskDetail(taskId)
    parseResults.value = res || []
  } catch (e) {
    ElMessage.error('获取详情失败')
  } finally {
    loading.value = false
  }
}

const downloadOriginalPdf = async () => {
  try {
    const blob: any = await downloadSourceFile(taskId)
    const filename = task.value?.filename || `source_${taskId}.pdf`
    downloadFile(blob, filename)
    ElMessage.success('下载成功')
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

const refreshProgress = async () => {
  const result: any = await getTranslationProgress(taskId)
  const { parseProgress, translateProgress, status, message } = result
  translationStore.updateTask(taskId, { parseProgress, translateProgress, status, message })
}

const stopPolling = () => {
  if (pollingTimer.value != null) {
    window.clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

const startPolling = () => {
  if (pollingTimer.value != null) return
  pollingTimer.value = window.setInterval(async () => {
    try {
      await refreshProgress()
      const current = task.value
      if (!current) return
      if (current.status !== 'processing' || (current.translateProgress ?? 0) >= 100) {
        stopPolling()
      }
    } catch {
      return
    }
  }, 1500)
}

const startTranslate = async () => {
  if (parseProgress.value < 100) {
    ElMessage.warning('解析未完成，无法开始翻译')
    return
  }
  if (translationProgress.value >= 100) {
    ElMessage.success('翻译已完成')
    return
  }

  translateSubmitting.value = true
  try {
    await submitTranslationTask(taskId)
    translationStore.updateTask(taskId, { status: 'processing', translateProgress: 0 })
    await refreshProgress()
    startPolling()
    ElMessage.success('翻译任务已提交')
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    ElMessage.error(detail || '提交翻译任务失败')
  } finally {
    translateSubmitting.value = false
  }
}

const setViewMode = (mode: 'parse' | 'translation' | 'compare') => {
  viewMode.value = mode
}

onMounted(() => {
  fetchDetail()
  refreshProgress()
    .then(() => {
      if (task.value?.status === 'processing') startPolling()
    })
    .catch(() => undefined)
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.detail-card {
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
}

.file-icon { color: #409eff; }

.header-actions { display: flex; gap: 8px; }

.meta-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.meta { color: #606266; }
.meta p { margin: 6px 0; }

.progress-rings {
  display: flex;
  gap: 12px;
  align-items: center;
  flex: 0 0 auto;
}

.ring-item {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.ring-wrapper {
  position: relative;
  width: 72px;
  height: 72px;
}

.ring-content {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ring-text {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.ring-icon-success {
  font-size: 22px;
  color: #67c23a;
}

.ring-icon-exception {
  font-size: 22px;
  color: #f56c6c;
}

.ring-label {
  font-size: 12px;
  color: #606266;
}

.result-empty {
  padding: 60px 0;
}

.markdown-preview {
  font-size: 14px;
  line-height: 1.6;
  max-height: 300px;
  overflow-y: auto;
}

.markdown-preview :deep(li) {
  display: list-item;
}

.edit-actions,
.normal-actions {
  display: flex;
  flex-direction: column;
  gap: 5px;
  align-items: center;
}

.edit-actions .el-button,
.normal-actions .el-button {
  width: 80%;
  margin-left: 0;
}
</style>
