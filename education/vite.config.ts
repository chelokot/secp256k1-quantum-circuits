import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5177,
    strictPort: false,
  },
  preview: {
    port: 4177,
    strictPort: false,
  },
});
