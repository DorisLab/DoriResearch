import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  define: { 'process.env.NODE_ENV': JSON.stringify('production') },
  build: {
    outDir: 'dist/desktop',
    lib: {
      entry: 'src/embedded/main.tsx',
      name: 'DorislabResearch',
      formats: ['iife'],
      fileName: () => 'research.js',
      cssFileName: 'research',
    },
  },
});
