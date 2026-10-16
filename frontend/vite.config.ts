import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: process.env.DORIRESEARCH_SERVICE_PORT
      ? {
          '/research-api': {
            target: `http://127.0.0.1:${process.env.DORIRESEARCH_SERVICE_PORT}`,
            rewrite: () => '/rpc',
            headers: { Authorization: `Bearer ${process.env.DORIRESEARCH_TOKEN}` },
          },
        }
      : undefined,
  },
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'chart-renderer', test: /node_modules[\\/](zrender)[\\/]/, priority: 30 },
            {
              name: 'chart-types',
              maxSize: 400_000,
              test: /node_modules[\\/]echarts[\\/]lib[\\/]chart[\\/]/,
              priority: 30,
            },
            {
              name: 'chart-components',
              test: /node_modules[\\/]echarts[\\/]lib[\\/]component[\\/]/,
              priority: 30,
            },
            { name: 'chart-core', test: /node_modules[\\/]echarts[\\/]/, priority: 20 },
            {
              name: 'react',
              test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/,
              priority: 20,
            },
            {
              name: 'markdown',
              test: /node_modules[\\/](react-markdown|remark[^\\/]*|micromark[^\\/]*|mdast[^\\/]*|hast[^\\/]*|unified|unist[^\\/]*)[\\/]/,
              priority: 20,
            },
          ],
        },
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
