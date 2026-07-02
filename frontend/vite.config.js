import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  // Base URL must match Django's STATIC_URL + app path
  base: '/static/core/dist/',
  build: {
    outDir: resolve(__dirname, '../core/static/core/dist'),
    emptyOutDir: true,
    reportCompressedSize: false,
    rollupOptions: {
      input: {
        'scenario-selector':   resolve(__dirname, 'src/entries/scenario-selector.js'),
        'roleplay-chat':       resolve(__dirname, 'src/entries/roleplay-chat.js'),
        'soft-skills-app':     resolve(__dirname, 'src/entries/soft-skills-app.js'),
      },
      output: {
        // Nombres predecibles sin hash para que los templates Django los referencien
        entryFileNames: '[name].js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: '[name][extname]',
      },
    },
  },
})
