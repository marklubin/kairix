import { useState, useEffect } from 'react'
import { useContextualAwareness } from '@/hooks/useContextualAwareness'
import { cn } from '@/lib/utils'
import { ChevronLeft, Wifi, WifiOff } from 'lucide-react'
import type { ContextUpdate } from '@/types/context'

interface SensorPanelProps {
  className?: string
}

export function SensorPanel({ className }: SensorPanelProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [dataCount, setDataCount] = useState({ context: 0, sensor: 0 })
  
  const {
    lastContextUpdate,
    triggerContextUpdate,
    sensorState,
    startSensorStream,
    stopSensorStream,
    isActive,
    hasPermissions,
    errors
  } = useContextualAwareness({
    enableContext: true,
    enableSensors: true,
    onContextUpdate: (update: ContextUpdate) => {
      console.log('Context update:', update)
      setDataCount(prev => ({ ...prev, context: prev.context + 1 }))
    },
    onSensorStateChange: (state) => {
      if (state.streaming) {
        setDataCount(prev => ({ ...prev, sensor: prev.sensor + 1 }))
      }
    }
  })
  
  // Auto-close panel when not active
  useEffect(() => {
    if (!isActive && isOpen) {
      setTimeout(() => setIsOpen(false), 1000)
    }
  }, [isActive, isOpen])
  
  const formatSensorStatus = () => {
    if (!sensorState.connected) return 'Disconnected'
    if (sensorState.streaming) return 'Streaming'
    return 'Connected'
  }
  
  const activeSensorCount = Object.values(sensorState.sensors).filter(s => s.active).length
  
  return (
    <>
      
      {/* Slide-out Panel */}
      <div
        className={cn(
          "fixed bottom-0 right-0 z-50",
          "bg-background border-l border-t",
          "transition-transform duration-300 ease-in-out",
          "w-80 h-96",
          "rounded-tl-lg shadow-2xl",
          isOpen ? "translate-x-0" : "translate-x-full",
          className
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <div className={cn(
              "w-2 h-2 rounded-full",
              isActive ? "bg-green-500" : "bg-muted-foreground"
            )} />
            <h3 className="font-medium">Sensor Stream</h3>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 hover:bg-accent rounded transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-4 space-y-4 overflow-y-auto h-[calc(100%-4rem)]">
          {/* Connection Status */}
          <div className="flex items-center justify-between p-3 bg-accent/50 rounded-lg">
            <div className="flex items-center gap-2">
              {sensorState.connected ? (
                <Wifi className="w-4 h-4 text-green-500" />
              ) : (
                <WifiOff className="w-4 h-4 text-red-500" />
              )}
              <span className="text-sm font-medium">
                {formatSensorStatus()}
              </span>
            </div>
            <button
              onClick={() => sensorState.streaming ? stopSensorStream() : startSensorStream()}
              className={cn(
                "px-3 py-1 rounded text-xs font-medium transition-colors",
                sensorState.streaming 
                  ? "bg-red-500 hover:bg-red-600 text-white"
                  : "bg-green-500 hover:bg-green-600 text-white"
              )}
            >
              {sensorState.streaming ? 'Stop' : 'Start'}
            </button>
          </div>
          
          {/* Active Sensors */}
          {sensorState.connected && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Active Sensors</span>
                <span className="font-mono">{activeSensorCount}/{Object.keys(sensorState.sensors).length}</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(sensorState.sensors).map(([sensor, state]) => (
                  <div
                    key={sensor}
                    className={cn(
                      "px-3 py-2 rounded-lg text-xs font-medium text-center transition-all",
                      state.active 
                        ? "bg-green-500/20 text-green-600 border border-green-500/30"
                        : "bg-muted text-muted-foreground"
                    )}
                  >
                    {sensor}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Data Flow Stats */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Data Flow</h4>
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Context Updates:</span>
                <span className="font-mono">{dataCount.context}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Sensor Messages:</span>
                <span className="font-mono">{dataCount.sensor}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Buffer Size:</span>
                <span className="font-mono">{sensorState.bufferedMessages}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Errors:</span>
                <span className="font-mono text-red-500">{sensorState.errorCount}</span>
              </div>
            </div>
          </div>
          
          {/* Last Context Update */}
          {lastContextUpdate && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Last Context</h4>
              <div className="text-xs space-y-1 font-mono bg-muted/50 p-2 rounded">
                {lastContextUpdate.contexts?.geolocation && (
                  <div>📍 {lastContextUpdate.contexts.geolocation.latitude.toFixed(4)}, {lastContextUpdate.contexts.geolocation.longitude.toFixed(4)}</div>
                )}
                {lastContextUpdate.contexts?.device && (
                  <div>💻 {lastContextUpdate.contexts.device.platform}</div>
                )}
                {lastContextUpdate.contexts?.activity && (
                  <div>🌐 {lastContextUpdate.contexts.activity.pageTitle}</div>
                )}
              </div>
            </div>
          )}
          
          {/* Actions */}
          <div className="pt-2 space-y-2">
            <button
              onClick={() => triggerContextUpdate('manual', 'high')}
              className="w-full px-3 py-2 bg-accent hover:bg-accent/80 rounded-lg text-sm font-medium transition-colors"
            >
              Update Context Now
            </button>
          </div>
          
          {/* Errors */}
          {errors.length > 0 && (
            <div className="space-y-1">
              <h4 className="text-sm font-medium text-red-500">Recent Errors</h4>
              <div className="text-xs text-red-500 space-y-1 bg-red-500/10 p-2 rounded">
                {errors.slice(-3).map((error, i) => (
                  <div key={i} className="truncate">{error}</div>
                ))}
              </div>
            </div>
          )}
          
          {/* Permissions Warning */}
          {!hasPermissions && (
            <div className="p-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
              <p className="text-xs text-yellow-600">
                ⚠️ Some permissions are required for full sensor functionality
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}