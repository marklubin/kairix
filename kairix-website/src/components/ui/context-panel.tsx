import { useState } from 'react'
import { useContextualAwareness } from '@/hooks/useContextualAwareness'
import { Button } from './button'
import { cn } from '@/lib/utils'
import type { ContextUpdate } from '@/types/context'

interface ContextPanelProps {
  className?: string
}

export function ContextPanel({ className }: ContextPanelProps) {
  const [expanded, setExpanded] = useState(false)
  const [showSensors, setShowSensors] = useState(false)
  
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
    enableSensors: showSensors,
    onContextUpdate: (update: ContextUpdate) => {
      console.log('Context update:', update)
    }
  })
  
  const formatLocation = () => {
    if (!lastContextUpdate?.contexts?.geolocation) return 'Unknown'
    const { latitude, longitude, accuracy } = lastContextUpdate.contexts.geolocation
    return `${latitude.toFixed(4)}, ${longitude.toFixed(4)} (±${accuracy?.toFixed(0)}m)`
  }
  
  const formatDevice = () => {
    if (!lastContextUpdate?.contexts?.device) return 'Unknown'
    const device = lastContextUpdate.contexts.device
    return `${device.platform} • ${device.onLine ? 'Online' : 'Offline'}`
  }
  
  const formatEnvironment = () => {
    if (!lastContextUpdate?.contexts?.environment) return 'Unknown'
    const env = lastContextUpdate.contexts.environment
    return `${env.timezone} • ${env.isDarkMode ? 'Dark' : 'Light'} mode`
  }
  
  const formatActivity = () => {
    if (!lastContextUpdate?.contexts?.activity) return 'Unknown'
    const activity = lastContextUpdate.contexts.activity
    const duration = Math.floor(activity.sessionDuration / 60000)
    return `${activity.pageTitle} • ${duration}min`
  }
  
  return (
    <div className={cn(
      "fixed bottom-4 right-4 bg-background border rounded-lg shadow-lg transition-all",
      expanded ? "w-96" : "w-48",
      className
    )}>
      {/* Header */}
      <div 
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-accent/50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <div className={cn(
            "w-2 h-2 rounded-full",
            isActive ? "bg-green-500 animate-pulse" : "bg-gray-500"
          )} />
          <span className="text-sm font-medium">Context Aware</span>
        </div>
        <button className="text-xs text-muted-foreground">
          {expanded ? '−' : '+'}
        </button>
      </div>
      
      {/* Content */}
      {expanded && (
        <>
          <div className="border-t px-3 py-2 space-y-2">
            {/* Context Data */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Location:</span>
                <span className="font-mono">{formatLocation()}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Device:</span>
                <span>{formatDevice()}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Environment:</span>
                <span>{formatEnvironment()}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Activity:</span>
                <span>{formatActivity()}</span>
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex gap-2 pt-2">
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => triggerContextUpdate('manual', 'high')}
                className="flex-1 text-xs"
              >
                Update Now
              </Button>
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => setShowSensors(!showSensors)}
                className="flex-1 text-xs"
              >
                {showSensors ? 'Hide' : 'Show'} Sensors
              </Button>
            </div>
            
            {/* Sensor Data */}
            {showSensors && (
              <div className="border-t pt-2 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">Sensor Stream</span>
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      sensorState.connected ? "bg-green-500" : "bg-red-500"
                    )} />
                    <span className="text-xs text-muted-foreground">
                      {sensorState.connected ? 'Connected' : 'Disconnected'}
                    </span>
                  </div>
                </div>
                
                {sensorState.connected && (
                  <div className="space-y-1">
                    <div className="grid grid-cols-3 gap-1 text-xs">
                      {Object.entries(sensorState.sensors).map(([sensor, state]) => (
                        <div 
                          key={sensor}
                          className={cn(
                            "px-2 py-1 rounded text-center",
                            state.active ? "bg-green-500/20" : "bg-gray-500/20"
                          )}
                        >
                          {sensor}
                        </div>
                      ))}
                    </div>
                    
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Messages buffered:</span>
                      <span>{sensorState.bufferedMessages}</span>
                    </div>
                    
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Error count:</span>
                      <span>{sensorState.errorCount}</span>
                    </div>
                  </div>
                )}
                
                <Button
                  size="sm"
                  variant={sensorState.streaming ? "destructive" : "default"}
                  onClick={() => sensorState.streaming ? stopSensorStream() : startSensorStream()}
                  className="w-full text-xs"
                >
                  {sensorState.streaming ? 'Stop Streaming' : 'Start Streaming'}
                </Button>
              </div>
            )}
            
            {/* Errors */}
            {errors.length > 0 && (
              <div className="border-t pt-2">
                <div className="text-xs text-red-500 space-y-1">
                  {errors.slice(-3).map((error, i) => (
                    <div key={i}>{error}</div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Permissions */}
            {!hasPermissions && (
              <div className="border-t pt-2">
                <div className="text-xs text-yellow-600">
                  ⚠️ Some permissions are required for full functionality
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}