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
                  <el-dropdown-item @click="setViewMode('compare')">双语对照</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-dropdown v-if="viewMode === 'compare'" trigger="hover" placement="bottom-end">
              <el-button size="small">
                对照模式
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="setCompareLayout('sourceFirst')">原文在上方</el-dropdown-item>
                  <el-dropdown-item @click="setCompareLayout('translationFirst')">译文在上方</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-checkbox v-model="showMetaInfo" label="显示段落信息" style="margin-left: 12px; margin-right: 8px;" />
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
        
        <div class="header-actions">
            <el-button v-if="isReordered" size="small" type="warning" @click="restoreOrder">
              还原排序
            </el-button>
        </div>
        <!-- 文档流显示结果 -->
        <div class="document-list" v-if="parseResults.length > 0">
          <div
            class="document-block"
            v-for="(row, i) in parseResults"
            :key="row.index"
            :draggable="dragIndex === row.index"
            @dragstart="onDragStart($event, i)"
            @dragover.prevent
            @dragenter.prevent
            @drop="onDrop($event, i)"
            @dragend="onDragEnd"
          >
            <div class="block-main">
              <div class="block-meta" v-if="showMetaInfo">
                <span>第 {{ row.pageNum }} 页</span>
                <el-tag size="small" type="info">{{ row.type }}</el-tag>
                <el-tag size="small" v-if="row.subType" type="info" effect="plain">{{ row.subType }}</el-tag>
              </div>

              <div class="block-content">
                <!-- 解析结果模式 -->
                <template v-if="viewMode === 'parse'">
                  <div class="edit-area" v-if="row.editingSource">
                    <el-input v-model="row.sourceBuffer" type="textarea" :autosize="{ minRows: 4, maxRows: 15 }" placeholder="请输入原文" />
                    <div class="edit-actions-row">
                      <el-button type="success" size="small" @click="saveSourceEdit(row)" :loading="saving" :disabled="saving">保存原文</el-button>
                      <el-button size="small" @click="cancelSourceEdit(row)" :disabled="saving">取消</el-button>
                    </div>
                  </div>
                  <div v-else class="markdown-preview markdown-body" v-html="renderMarkdown(row.markdownContent)"></div>
                </template>

                <!-- 翻译结果模式 -->
                <template v-if="viewMode === 'translation'">
                  <div class="edit-area" v-if="row.editingTranslation">
                    <el-input v-model="row.translationBuffer" type="textarea" :autosize="{ minRows: 4, maxRows: 15 }" placeholder="请输入译文" />
                    <div class="edit-actions-row">
                      <el-button type="success" size="small" @click="saveTranslationEdit(row)" :loading="translationSaving" :disabled="translationSaving">保存译文</el-button>
                      <el-button size="small" @click="cancelTranslationEdit(row)" :disabled="translationSaving">取消</el-button>
                    </div>
                  </div>
                  <div v-else class="markdown-preview markdown-body" v-html="renderMarkdown(row.translatedMarkdownContent || row.markdownContent)"></div>
                </template>

                <!-- 双语对照模式 -->
                <template v-if="viewMode === 'compare'">
                  <template v-if="compareLayout === 'sourceFirst'">
                    <div class="compare-item source-item">
                      <div class="edit-area" v-if="row.editingSource">
                        <el-input v-model="row.sourceBuffer" type="textarea" :autosize="{ minRows: 4, maxRows: 15 }" placeholder="请输入原文" />
                        <div class="edit-actions-row">
                          <el-button type="success" size="small" @click="saveSourceEdit(row)" :loading="saving" :disabled="saving">保存原文</el-button>
                          <el-button size="small" @click="cancelSourceEdit(row)" :disabled="saving">取消</el-button>
                        </div>
                      </div>
                      <div v-else class="markdown-preview markdown-body" v-html="renderMarkdown(row.markdownContent)"></div>
                    </div>
                    <div class="compare-item translation-item">
                      <div class="edit-area" v-if="row.editingTranslation">
                        <el-input v-model="row.translationBuffer" type="textarea" :autosize="{ minRows: 4, maxRows: 15 }" placeholder="请输入译文" />
                        <div class="edit-actions-row">
                          <el-button type="success" size="small" @click="saveTranslationEdit(row)" :loading="translationSaving" :disabled="translationSaving">保存译文</el-button>
                          <el-button size="small" @click="cancelTranslationEdit(row)" :disabled="translationSaving">取消</el-button>
                        </div>
                      </div>
                      <div v-else class="markdown-preview markdown-body" v-html="renderMarkdown(row.translatedMarkdownContent || row.markdownContent)"></div>
                    </div>
                  </template>
                  <template v-else>
                    <div class="compare-item translation-item">
                      <div class="edit-area" v-if="row.editingTranslation">
                        <el-input v-model="row.translationBuffer" type="textarea" :autosize="{ minRows: 4, maxRows: 15 }" placeholder="请输入译文" />
                        <div class="edit-actions-row">
                          <el-button type="success" size="small" @click="saveTranslationEdit(row)" :loading="translationSaving" :disabled="translationSaving">保存译文</el-button>
                          <el-button size="small" @click="cancelTranslationEdit(row)" :disabled="translationSaving">取消</el-button>
                        </div>
                      </div>
                      <div v-else class="markdown-preview markdown-body" v-html="renderMarkdown(row.translatedMarkdownContent || row.markdownContent)"></div>
                    </div>
                    <div class="compare-item source-item">
                      <div class="edit-area" v-if="row.editingSource">
                        <el-input v-model="row.sourceBuffer" type="textarea" :autosize="{ minRows: 4, maxRows: 15 }" placeholder="请输入原文" />
                        <div class="edit-actions-row">
                          <el-button type="success" size="small" @click="saveSourceEdit(row)" :loading="saving" :disabled="saving">保存原文</el-button>
                          <el-button size="small" @click="cancelSourceEdit(row)" :disabled="saving">取消</el-button>
                        </div>
                      </div>
                      <div v-else class="markdown-preview markdown-body" v-html="renderMarkdown(row.markdownContent)"></div>
                    </div>
                  </template>
                </template>
              </div>

              <!-- 评论区 -->
              <div class="comments-section" v-if="row.showComments">
                <el-divider>评论</el-divider>
                <div class="comment-list" v-if="row.comments && row.comments.length > 0">
                  <div class="comment-item" v-for="c in row.comments" :key="c.id">
                    <div class="comment-time">{{ c.time }}</div>
                    <div class="comment-text">{{ c.text }}</div>
                  </div>
                </div>
                <el-empty v-else description="暂无评论" :image-size="40" />
                <div class="add-comment">
                  <el-input v-model="row.newComment" placeholder="添加新评论..." size="small" @keyup.enter="submitComment(row)" />
                  <el-button type="primary" size="small" @click="submitComment(row)">提交</el-button>
                </div>
              </div>
            </div>

            <!-- 右侧操作列 -->
            <div class="block-actions-col">
              <div
                class="drag-handle action-btn"
                title="拖动以重新排序"
                @mousedown="dragIndex = row.index"
                @mouseup="dragIndex = null"
                @mouseleave="dragIndex = null"
              >
                <el-icon><Rank /></el-icon>
              </div>
              <div class="action-btn" title="编辑原文" v-if="viewMode === 'parse' || viewMode === 'compare'" @click="startSourceEdit(row)">
                编辑原文
              </div>
              <div class="action-btn" title="编辑译文" v-if="viewMode === 'translation' || viewMode === 'compare'" @click="startTranslationEdit(row)">
                编辑译文
              </div>
              <div class="action-btn" title="评论" @click="toggleComment(row)">
                评论 ({{ (row.comments || []).length }})
              </div>
            </div>
          </div>
        </div>

        <el-empty
          v-else
          description="暂无内容"
          class="result-empty"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Download, Check, Close, Rank } from '@element-plus/icons-vue'
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
const translationSaving = ref(false)
const viewMode = ref<'parse' | 'translation' | 'compare'>('parse')
const compareLayout = ref<'sourceFirst' | 'translationFirst'>('sourceFirst')
const translateSubmitting = ref(false)
const pollingTimer = ref<number | null>(null)
const isReordered = ref(false)
const showMetaInfo = ref(true)
const dragIndex = ref<number | null>(null)

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

const startSourceEdit = (row: any) => {
  row.editingSource = true
  row.sourceBuffer = row.markdownContent
}

const cancelSourceEdit = (row: any) => {
  row.editingSource = false
}

const saveSourceEdit = async (row: any) => {
  saving.value = true
  try {
    await updateTaskResult(taskId, row.index, { markdownContent: row.sourceBuffer })
    row.markdownContent = row.sourceBuffer
    row.editingSource = false
    ElMessage.success('原文保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const startTranslationEdit = (row: any) => {
  row.editingTranslation = true
  row.translationBuffer = row.translatedMarkdownContent || row.markdownContent
}

const cancelTranslationEdit = (row: any) => {
  row.editingTranslation = false
}

const saveTranslationEdit = async (row: any) => {
  translationSaving.value = true
  try {
    await updateTaskResult(taskId, row.index, { translatedMarkdownContent: row.translationBuffer })
    row.translatedMarkdownContent = row.translationBuffer
    row.editingTranslation = false
    ElMessage.success('译文保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    translationSaving.value = false
  }
}

const toggleComment = (row: any) => {
  row.showComments = !row.showComments
}

const submitComment = (row: any) => {
  if (!row.newComment?.trim()) return
  if (!row.comments) row.comments = []

  // Mock API behavior for comment
  row.comments.push({
    id: Date.now().toString(),
    text: row.newComment,
    time: new Date().toLocaleString()
  })
  row.newComment = ''
  ElMessage.success('评论已保存')
}

let draggedIndex = -1

const onDragStart = (e: DragEvent, index: number) => {
  draggedIndex = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.dropEffect = 'move'
  }
}

const onDrop = (e: DragEvent, dropIndex: number) => {
  if (draggedIndex === -1 || draggedIndex === dropIndex) return
  const item = parseResults.value.splice(draggedIndex, 1)[0]
  parseResults.value.splice(dropIndex, 0, item)
  draggedIndex = -1
  isReordered.value = true
  dragIndex.value = null
  ElMessage.success('排序已保存 (前端模拟)')
}

const onDragEnd = () => {
  dragIndex.value = null
}

const restoreOrder = () => {
  parseResults.value.sort((a, b) => a.originalIndex - b.originalIndex)
  isReordered.value = false
  ElMessage.success('已恢复原始顺序')
}

const fetchDetail = async () => {
  loading.value = true
  try {
    const res: any = await getTaskDetail(taskId)
    parseResults.value = (res || []).map((item: any, idx: number) => ({
      ...item,
      originalIndex: idx,
      comments: [],
      showComments: false,
      newComment: '',
      editingSource: false,
      editingTranslation: false,
      sourceBuffer: '',
      translationBuffer: ''
    }))
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
  if (task.value?.status === 'processing' && translationProgress.value < 100) {
    startPolling()
    ElMessage.info('翻译进行中，请稍候')
    return
  }
  if (translationProgress.value >= 100) {
    try {
      await ElMessageBox.confirm('该任务已翻译完成，是否再次翻译？', '再次翻译确认', {
        confirmButtonText: '再次翻译',
        cancelButtonText: '取消',
        type: 'warning'
      })
    } catch {
      return
    }
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

const setCompareLayout = (layout: 'sourceFirst' | 'translationFirst') => {
  compareLayout.value = layout
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

.document-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 10px 0;
}

.document-block {
  background-color: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  transition: box-shadow 0.3s;
  display: flex;
  gap: 16px;
}

.document-block:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.block-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.block-actions-col {
  flex: 0 0 100px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding-left: 16px;
  border-left: 1px dashed #e4e7ed;
}

.action-btn {
  font-size: 13px;
  color: #409eff;
  cursor: pointer;
  user-select: none;
}

.action-btn:hover {
  color: #66b1ff;
  text-decoration: underline;
}

.drag-handle {
  cursor: grab;
  font-size: 18px;
  color: #909399;
  text-decoration: none !important;
}

.drag-handle:active {
  cursor: grabbing;
}

.block-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
  font-size: 12px;
  color: #909399;
}

.edit-actions-row {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.comments-section {
  margin-top: 16px;
  background: #fcfcfc;
  padding: 12px;
  border-radius: 4px;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.comment-item {
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 8px;
}

.comment-time {
  font-size: 11px;
  color: #a8abb2;
  margin-bottom: 4px;
}

.comment-text {
  font-size: 13px;
  color: #606266;
}

.add-comment {
  display: flex;
  gap: 8px;
}

.block-content {
  display: flex;
  flex-direction: column;
}

.compare-item {
  margin-bottom: 12px;
}

.compare-item:last-child {
  margin-bottom: 0;
}

.source-item {
  color: #303133;
}

.translation-item {
  color: #606266;
}
</style>
