const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    port: 8080,
    // 过滤浏览器 ResizeObserver 警告，避免被 dev server 当成致命错误弹出覆盖层
    client: {
      overlay: {
        runtimeErrors: (error) => {
          const ignoreList = [
            'ResizeObserver loop completed with undelivered notifications',
            'ResizeObserver loop limit exceeded',
          ]
          return !ignoreList.some((msg) => (error && error.message ? error.message : String(error)).includes(msg))
        },
      },
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
