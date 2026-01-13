<template>
  <div id="app">
    <el-container class="layout-container">
      <!-- 左侧菜单栏 -->
      <el-aside :width="isCollapse ? '64px' : '200px'" class="app-aside">
        <div class="logo-container">
          <h1 class="app-title" v-show="!isCollapse">PDF翻译器</h1>
          <h1 class="app-title-mini" v-show="isCollapse">PDF</h1>
        </div>
        <el-menu
          :default-active="$route.path"
          class="nav-menu"
          :collapse="isCollapse"
          router
        >
          <el-menu-item index="/">
            <el-icon><Upload /></el-icon>
            <template #title>上传PDF</template>
          </el-menu-item>
          <el-menu-item index="/list">
            <el-icon><Document /></el-icon>
            <template #title>翻译列表</template>
          </el-menu-item>
          <el-menu-item index="/config">
            <el-icon><Setting /></el-icon>
            <template #title>配置设置</template>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 右侧内容区 -->
      <el-container class="main-container">
        <el-header class="app-header">
          <div class="header-left">
            <el-icon class="collapse-btn" @click="toggleCollapse">
              <Expand v-if="isCollapse" />
              <Fold v-else />
            </el-icon>
          </div>
        </el-header>

        <el-main class="app-main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Upload, Document, Setting, Fold, Expand } from '@element-plus/icons-vue'

const isCollapse = ref(false)

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.app-aside {
  background-color: #fff;
  border-right: 1px solid #e4e7ed;
  transition: width 0.3s;
  display: flex;
  flex-direction: column;
}

.logo-container {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #e4e7ed;
  overflow: hidden;
}

.app-title {
  margin: 0;
  color: #2563eb;
  font-size: 20px;
  font-weight: 600;
  white-space: nowrap;
}

.app-title-mini {
  margin: 0;
  color: #2563eb;
  font-size: 16px;
  font-weight: 600;
}

.nav-menu {
  border-right: none;
  flex: 1;
}

.main-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  height: 60px;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
}

.collapse-btn:hover {
  color: #409eff;
}

.app-main {
  flex: 1;
  background-color: #f5f7fa;
  padding: 20px;
  overflow-y: auto; /* 关键：实现内容区域独立滚动 */
}
</style>
