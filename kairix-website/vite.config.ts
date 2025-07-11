import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode, command }) => {
  // Load env file based on `mode` in the current working directory.
  const env = loadEnv(mode, process.cwd(), '')
  
  // Only check env vars when serving, not building
  if (command === 'serve') {
    const websitePort = parseInt(env.KAIRIX_WEBSITE_PORT)
    const elevenLabsApiKey = env.ELEVENLABS_API_KEY
    
    if (!websitePort) {
      throw new Error('KAIRIX_WEBSITE_PORT environment variable is required')
    }
    
    if (!elevenLabsApiKey) {
      throw new Error('ELEVENLABS_API_KEY environment variable is required')
    }
  }
  
  // Use env vars if available, otherwise use defaults for build
  const websitePort = parseInt(env.KAIRIX_WEBSITE_PORT) || 5173
  const elevenLabsApiKey = env.ELEVENLABS_API_KEY || ''
  const hmrHost = env.VITE_HMR_HOST || 'localhost'

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    define: {
      // Re-export required env vars with VITE_ prefix for client code
      'import.meta.env.VITE_KAIRIX_WEBSITE_PORT': JSON.stringify(websitePort.toString()),
      'import.meta.env.VITE_ELEVENLABS_API_KEY': JSON.stringify(elevenLabsApiKey),
    },
    server: {
      host: '0.0.0.0', // Bind to all interfaces for production
      port: websitePort,
      strictPort: true, // Use strict port to ensure we use the configured port
      cors: true, // Enable CORS
      allowedHosts: ['dev.kairix.net', 'localhost', '.kairix.net'], // Allow access from these hosts
      hmr: {
        host: 'localhost',
        port: websitePort,
      },
    },
  }
})
