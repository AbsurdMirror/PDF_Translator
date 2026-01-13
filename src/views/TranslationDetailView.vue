<template>
  <div class="detail-container">
    <el-card class="detail-card">
      <template #header>
        <div class="card-header">
          <div class="title-group">
            <el-icon class="file-icon"><Document /></el-icon>
            <span class="title-text">翻译结果详情</span>
          </div>
          <div class="header-actions">
            <el-select v-model="scheme" size="small" style="width: 220px" @change="fetchDetail">
              <el-option label="方案A：双语对照块(pair-block)" value="pair-block" />
              <el-option label="方案B：表格双列(table-two-col)" value="table-two-col" />
            </el-select>
            <el-button size="small" @click="$router.back()">
              返回
            </el-button>
            <el-button type="primary" size="small" :disabled="task?.status !== 'completed'" @click="downloadTask()">
              <el-icon><Download /></el-icon>
              下载结果
            </el-button>
          </div>
        </div>
      </template>

      <div v-if="loading" class="loading-area">
        <el-skeleton :rows="6" animated />
      </div>
      <div v-else>
        <div class="meta">
          <p><strong>文件名：</strong>{{ task?.filename }}</p>
          <p><strong>任务ID：</strong>{{ taskId }}</p>
          <p><strong>创建时间：</strong>{{ task?.createTime }}</p>
        </div>
        <div class="markdown-body" v-html="renderedHtml"></div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document, Download } from '@element-plus/icons-vue'
import { useTranslationStore } from '@/stores/translation'
import { mockGetTaskDetail, mockDownloadTranslation } from '@/services/mockApi'
import { downloadFile } from '@/utils'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js'
import 'github-markdown-css/github-markdown.css'
import 'highlight.js/styles/github.css'

const route = useRoute()
const translationStore = useTranslationStore()

const taskId = route.params.taskId as string
const loading = ref(true)
const scheme = ref<'pair-block' | 'table-two-col'>('pair-block')
const markdown = ref('')
const task = computed(() => translationStore.tasks.find((t) => t.taskId === taskId))

marked.use({
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

const renderedHtml = computed(() => {
  const html = marked.parse(markdown.value, { async: false }) as string
  return DOMPurify.sanitize(html)
})

const fetchDetail = async () => {
  loading.value = true
  try {
    const res = await mockGetTaskDetail(taskId, scheme.value)
    markdown.value = res.content
  } catch (e) {
    ElMessage.error('获取详情失败')
  } finally {
    loading.value = false
  }
}

const downloadTask = async () => {
  if (!task.value || task.value.status !== 'completed') return
  try {
    const blob: any = await mockDownloadTranslation(task.value.taskId)
    const filename = task.value.filename.replace('.pdf', '_translated.pdf')
    downloadFile(blob, filename)
    ElMessage.success('下载成功')
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

onMounted(() => {
  fetchDetail()
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

.meta { margin-bottom: 16px; color: #606266; }
.meta p { margin: 6px 0; }

.markdown-body { font-size: 14px; line-height: 1.8; }
.markdown-body h1, .markdown-body h2, .markdown-body h3 { margin: 12px 0; }
.markdown-body pre { background:#f5f7fa; padding:12px; border-radius:6px; overflow:auto; }
.markdown-body code { background:#f0f0f0; padding:2px 4px; border-radius:4px; }
.markdown-body .pair { margin: 12px 0; padding: 8px 12px; border:1px solid #e5e7eb; border-radius:8px; background:#fafafa; }
.markdown-body .pair-en { color:#111827; margin:0 0 4px; }
.markdown-body .pair-zh { color:#374151; margin:0; }
.markdown-body table { width:100%; border-collapse: collapse; }
.markdown-body table tr { border-bottom: 1px dashed #e5e7eb; }
.markdown-body table td, .markdown-body table th { padding: 10px 12px; }
.markdown-body table td:first-child { color:#111827; font-weight:500; }
.markdown-body table td:last-child { color:#374151; }
</style>
