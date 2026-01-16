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
            <el-button size="small" @click="$router.back()">
              返回
            </el-button>
            <el-button type="primary" size="small" :disabled="task?.status !== 'completed'" @click="downloadTask()">
              <el-icon><Download /></el-icon>
              下载原始PDF
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
        
        <!-- 解析结果表格 -->
        <el-table :data="parseResults" style="width: 100%" border stripe>
          <el-table-column prop="pageNum" label="页码" width="80" align="center" />
          <el-table-column prop="type" label="类型" width="100" align="center" />
          <el-table-column prop="subType" label="子类型" width="120" align="center">
             <template #default="{ row }">
               {{ row.subType || '-' }}
             </template>
          </el-table-column>
          <el-table-column prop="markdownContent" label="内容 (Markdown)">
            <template #default="{ row }">
              <div class="markdown-preview markdown-body" v-html="renderMarkdown(row.markdownContent)"></div>
            </template>
          </el-table-column>
        </el-table>
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
import { getTaskDetail, downloadSourceFile } from '@/services/api'
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

const renderMarkdown = (content: string) => {
  if (!content) return ''
  const html = marked.parse(content, { async: false }) as string
  return DOMPurify.sanitize(html)
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

const downloadTask = async () => {
  if (!task.value) return
  try {
    const blob: any = await downloadSourceFile(task.value.taskId)
    // 使用原始文件名
    const filename = task.value.filename 
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

.markdown-preview {
  font-size: 14px;
  line-height: 1.6;
  max-height: 300px;
  overflow-y: auto;
}
</style>
