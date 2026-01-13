<template>
  <div class="config-container">
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>配置设置</span>
          <el-tag type="info">保存后生效</el-tag>
        </div>
      </template>

      <el-form
        ref="configFormRef"
        :model="configForm"
        :rules="formRules"
        label-width="120px"
        class="config-form"
      >
        <el-divider content-position="left">阿里云基础配置</el-divider>

        <el-form-item label="Access Key ID" prop="aliyunAccessKeyId">
          <el-input
            v-model="configForm.aliyunAccessKeyId"
            type="password"
            show-password
            placeholder="请输入 Access Key ID"
            autocomplete="off"
          />
        </el-form-item>

        <el-form-item label="Access Key Secret" prop="aliyunAccessKeySecret">
          <el-input
            v-model="configForm.aliyunAccessKeySecret"
            type="password"
            show-password
            placeholder="请输入 Access Key Secret"
            autocomplete="off"
          />
        </el-form-item>

        <el-form-item label="区域" prop="aliyunRegion">
          <el-input v-model="configForm.aliyunRegion" placeholder="例如：cn-hangzhou" />
        </el-form-item>

        <el-form-item label="API端点" prop="aliyunEndpoint">
          <el-input
            v-model="configForm.aliyunEndpoint"
            placeholder="例如：https://docmind-api.cn-hangzhou.aliyuncs.com"
          />
        </el-form-item>

        <el-divider content-position="left">LLM配置</el-divider>

        <el-form-item label="API Key" prop="llmApiKey">
          <el-input
            v-model="configForm.llmApiKey"
            type="password"
            show-password
            placeholder="请输入 LLM API Key"
            autocomplete="off"
          />
        </el-form-item>

        <el-form-item label="模型名称" prop="llmModel">
          <el-input v-model="configForm.llmModel" placeholder="例如：qwen3-max" />
        </el-form-item>

        <el-form-item label="API端点" prop="llmEndpoint">
          <el-input
            v-model="configForm.llmEndpoint"
            placeholder="例如：https://dashscope.aliyuncs.com/compatible-mode/v1"
          />
        </el-form-item>
      </el-form>

      <!-- 操作按钮 -->
      <div class="form-actions">
        <el-button @click="resetForm">重置</el-button>
        <el-button type="primary" @click="saveConfigForm" :loading="saving"> 保存配置 </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useTranslationStore } from '@/stores/translation'
import type { TranslationConfig } from '@/stores/translation'
import { getConfig, saveConfig } from '@/services/api'

const translationStore = useTranslationStore()

const configFormRef = ref<FormInstance>()

const configForm = reactive({
  aliyunAccessKeyId: '',
  aliyunAccessKeySecret: '',
  aliyunRegion: '',
  aliyunEndpoint: 'https://docmind-api.cn-hangzhou.aliyuncs.com',
  llmApiKey: '',
  llmModel: '',
  llmEndpoint: 'https://dashscope.aliyuncs.com/compatible-mode/v1'
})

const formRules: FormRules = {
  aliyunAccessKeyId: [{ required: true, message: '请输入 Access Key ID', trigger: 'blur' }],
  aliyunAccessKeySecret: [{ required: true, message: '请输入 Access Key Secret', trigger: 'blur' }],
  aliyunEndpoint: [{ required: true, message: '请输入阿里云 API 端点', trigger: 'blur' }],
  llmApiKey: [{ required: true, message: '请输入 LLM API Key', trigger: 'blur' }],
  llmModel: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  llmEndpoint: [{ required: true, message: '请输入 LLM API 端点', trigger: 'blur' }]
}

// 状态管理
const saving = ref(false)

// 重置表单
const resetForm = async () => {
  await loadCurrentConfig()
  configFormRef.value?.clearValidate()
  ElMessage.info('已重置为当前保存的配置')
}

// 保存配置
const saveConfigForm = async () => {
  saving.value = true

  try {
    await configFormRef.value?.validate()

    const config: TranslationConfig = {
      aliyunAccessKeyId: configForm.aliyunAccessKeyId,
      aliyunAccessKeySecret: configForm.aliyunAccessKeySecret,
      aliyunRegion: configForm.aliyunRegion,
      aliyunEndpoint: configForm.aliyunEndpoint,
      llmApiKey: configForm.llmApiKey,
      llmModel: configForm.llmModel,
      llmEndpoint: configForm.llmEndpoint
    }

    // 调用 API 保存配置
    await saveConfig(config)

    // 保存到store
    translationStore.updateConfig(config)

    ElMessage.success('配置保存成功')
  } catch (error) {
    ElMessage.error('保存配置失败')
    console.error('保存配置错误:', error)
  } finally {
    saving.value = false
  }
}

// 加载当前配置
const loadCurrentConfig = async () => {
  try {
    const currentConfig: any = await getConfig()
    Object.assign(configForm, {
      aliyunAccessKeyId: currentConfig.aliyunAccessKeyId || '',
      aliyunAccessKeySecret: currentConfig.aliyunAccessKeySecret || '',
      aliyunRegion: currentConfig.aliyunRegion || '',
      aliyunEndpoint:
        currentConfig.aliyunEndpoint || 'https://docmind-api.cn-hangzhou.aliyuncs.com',
      llmApiKey: currentConfig.llmApiKey || '',
      llmModel: currentConfig.llmModel || '',
      llmEndpoint: currentConfig.llmEndpoint || 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    })
    // 同时更新 store
    translationStore.updateConfig(currentConfig)
  } catch (error) {
    ElMessage.error('加载配置失败')
    console.error('加载配置错误:', error)
  }
}

// 生命周期
onMounted(() => {
  loadCurrentConfig()
})
</script>

<style scoped>
.config-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.config-card {
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

.config-form {
  padding: 20px 0;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

@media (max-width: 768px) {
  .config-container {
    padding: 16px;
  }

  .config-form {
    padding: 16px 0;
  }

  .form-actions {
    flex-direction: column;
  }
}
</style>
