import { useEffect, useState } from 'react'
import { ContextService } from '@/services/context/ContextService'

export function ContextDebug() {
  interface DebugInfo {
    capabilities?: Record<string, boolean>
    context?: any
    locationPermission?: string
    userAgent?: string
    platform?: string
    apiUrl?: string
    apiKey?: string
    errors?: string[]
  }
  
  const [debugInfo, setDebugInfo] = useState<DebugInfo>({})
  
  useEffect(() => {
    const checkContext = async () => {
      const contextService = ContextService.getInstance()
      
      try {
        // Check basic browser capabilities
        const capabilities = {
          geolocation: 'geolocation' in navigator,
          deviceMotion: 'DeviceMotionEvent' in window,
          deviceOrientation: 'DeviceOrientationEvent' in window,
          ambientLight: 'AmbientLightSensor' in window,
          battery: 'getBattery' in navigator,
          connection: 'connection' in navigator || 'mozConnection' in navigator,
          permissions: 'permissions' in navigator
        }
        
        // Try to collect context
        const context = await contextService.collectAllContext()
        
        // Check permissions
        let locationPermission = 'unknown'
        if ('permissions' in navigator) {
          try {
            const result = await navigator.permissions.query({ name: 'geolocation' })
            locationPermission = result.state
          } catch (e) {
            locationPermission = 'error'
          }
        }
        
        setDebugInfo({
          capabilities,
          context,
          locationPermission,
          userAgent: navigator.userAgent,
          platform: navigator.platform,
          apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
          apiKey: localStorage.getItem('apiKey') || 'not set',
          errors: []
        })
      } catch (error) {
        setDebugInfo((prev: DebugInfo) => ({
          ...prev,
          errors: [...(prev.errors || []), error instanceof Error ? error.message : String(error)]
        }))
      }
    }
    
    checkContext()
  }, [])
  
  return (
    <div className="fixed bottom-20 right-4 bg-background border rounded-lg p-4 max-w-md max-h-96 overflow-auto text-xs font-mono">
      <h3 className="font-bold mb-2">Context Debug Info</h3>
      
      <div className="mb-2">
        <strong>API URL:</strong> {debugInfo.apiUrl}
      </div>
      
      <div className="mb-2">
        <strong>Location Permission:</strong> {debugInfo.locationPermission}
      </div>
      
      <div className="mb-2">
        <strong>Capabilities:</strong>
        <pre>{JSON.stringify(debugInfo.capabilities, null, 2)}</pre>
      </div>
      
      <div className="mb-2">
        <strong>Context Data:</strong>
        <pre>{JSON.stringify(debugInfo.context, null, 2)}</pre>
      </div>
      
      {debugInfo.errors && debugInfo.errors.length > 0 && (
        <div className="mb-2 text-red-500">
          <strong>Errors:</strong>
          <pre>{JSON.stringify(debugInfo.errors, null, 2)}</pre>
        </div>
      )}
      
      <button 
        onClick={() => window.location.reload()} 
        className="mt-2 px-2 py-1 bg-blue-500 text-white rounded text-xs"
      >
        Refresh
      </button>
    </div>
  )
}