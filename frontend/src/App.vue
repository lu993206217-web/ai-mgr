<template>
  <div id="app">
    <!-- 路由视图 -->
    <router-view />
  </div>
</template>

<script setup lang="ts">
// 应用初始化已在 main.ts 中完成，此处无需重复调用
</script>

<style>
/* 全局样式已在 style.css 中定义 */
#app {
  width: 100%;
  height: 100vh;
  overflow: hidden;
}
</style>
