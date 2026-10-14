import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) =>
          id.includes('/echarts/') || id.includes('/zrender/') ? 'charts' : undefined,
      },
    },
  },
  test: {
    // 同一组测试的 4 workers 比默认并行和 2 workers 更快，隔离契约不变。
    maxWorkers: 4,
    isolate: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    clearMocks: true,
  },
});
