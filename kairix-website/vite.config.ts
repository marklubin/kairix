import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  const env = loadEnv(mode, process.cwd(), '')
  // Get the website port from environment variable
  const websitePort = parseInt(env.KAIRIX_WEBSITE_PORT)
  
  if (!websitePort) {
    throw new Error('KAIRIX_WEBSITE_PORT environment variable is required')
  }
  
  // Get HMR host from environment or use default
  const hmrHost = env.VITE_HMR_HOST || 'localhost'

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    define: {
      // Re-export KAIRIX_WEBSITE_PORT as VITE_KAIRIX_WEBSITE_PORT for client code
      'import.meta.env.VITE_KAIRIX_WEBSITE_PORT': JSON.stringify(websitePort.toString()),
    },
    server: {
      host: 'localhost', // Use localhost only
      port: websitePort,
      strictPort: true, // Use strict port to ensure we use the configured port
      cors: true, // Enable CORS
      hmr: {
        host: 'localhost',
        port: websitePort,
      },
    },
  }
})
