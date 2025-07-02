import { useEffect, useState } from 'react'

export function DebugPanel() {
  const [logs, setLogs] = useState<string[]>([])
  const [apiKey, setApiKey] = useState<string>('')

  useEffect(() => {
    // Capture console.log
    const originalLog = console.log
    const originalError = console.error
    const originalWarn = console.warn

    console.log = (...args) => {
      originalLog(...args)
      setLogs(prev => [...prev, `[LOG] ${args.join(' ')}`].slice(-50))
    }

    console.error = (...args) => {
      originalError(...args)
      setLogs(prev => [...prev, `[ERROR] ${args.join(' ')}`].slice(-50))
    }

    console.warn = (...args) => {
      originalWarn(...args)
      setLogs(prev => [...prev, `[WARN] ${args.join(' ')}`].slice(-50))
    }

    // Check API key
    const key = localStorage.getItem('kairix-auth-key')
    setApiKey(key || 'NO KEY FOUND')

    return () => {
      console.log = originalLog
      console.error = originalError
      console.warn = originalWarn
    }
  }, [])

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-black/90 text-white p-2 max-h-40 overflow-y-auto text-xs font-mono z-[200]">
      <div className="text-yellow-400 mb-1">API Key: {apiKey.substring(0, 10)}...</div>
      {logs.map((log, i) => (
        <div key={i} className={log.includes('[ERROR]') ? 'text-red-400' : log.includes('[WARN]') ? 'text-yellow-400' : ''}>
          {log}
        </div>
      ))}
    </div>
  )
}