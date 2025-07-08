import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

interface TrackingIndicatorProps {
  isActive: boolean
  contextUpdates?: number
  sensorData?: number
  className?: string
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
}

export function TrackingIndicator({ 
  isActive, 
  contextUpdates = 0,
  sensorData = 0,
  className,
  position = 'top-right'
}: TrackingIndicatorProps) {
  const [pulseAnimation, setPulseAnimation] = useState(false)
  const [dataPoints, setDataPoints] = useState<{ time: number; type: 'context' | 'sensor' }[]>([])
  
  // Track data flow
  useEffect(() => {
    const now = Date.now()
    setDataPoints(prev => {
      const updated = [...prev]
      
      // Add new context updates
      for (let i = prev.filter(p => p.type === 'context').length; i < contextUpdates; i++) {
        updated.push({ time: now, type: 'context' })
      }
      
      // Add new sensor data
      for (let i = prev.filter(p => p.type === 'sensor').length; i < sensorData; i++) {
        updated.push({ time: now, type: 'sensor' })
      }
      
      // Keep only last 20 data points or last 5 seconds
      return updated.filter(p => now - p.time < 5000).slice(-20)
    })
    
    // Trigger pulse animation
    if (contextUpdates > 0 || sensorData > 0) {
      setPulseAnimation(true)
      setTimeout(() => setPulseAnimation(false), 500)
    }
  }, [contextUpdates, sensorData])
  
  // Position classes
  const positionClasses = {
    'top-left': 'top-4 left-4',
    'top-right': 'top-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'bottom-right': 'bottom-4 right-4'
  }
  
  if (!isActive) return null
  
  return (
    <div className={cn(
      "fixed z-50 pointer-events-none",
      positionClasses[position],
      className
    )}>
      {/* Main indicator */}
      <div className="bg-background/80 backdrop-blur-sm border rounded-lg shadow-lg p-3 pointer-events-auto">
        <div className="flex items-center gap-3">
          {/* Status dot */}
          <div className="relative">
            <div className={cn(
              "w-3 h-3 rounded-full transition-all",
              isActive ? "bg-green-500" : "bg-gray-500",
              pulseAnimation && "animate-ping"
            )} />
            <div className={cn(
              "absolute inset-0 w-3 h-3 rounded-full",
              isActive ? "bg-green-500" : "bg-gray-500"
            )} />
          </div>
          
          {/* Label */}
          <span className="text-xs font-medium text-muted-foreground">
            Tracking Active
          </span>
          
          {/* Data flow visualization */}
          <div className="flex gap-0.5">
            {dataPoints.map((point, i) => (
              <div
                key={i}
                className={cn(
                  "w-1 h-3 rounded-full transition-all",
                  point.type === 'context' ? "bg-blue-500" : "bg-purple-500",
                  "opacity-" + Math.max(20, 100 - (Date.now() - point.time) / 50)
                )}
                style={{
                  opacity: Math.max(0.2, 1 - (Date.now() - point.time) / 5000)
                }}
              />
            ))}
          </div>
        </div>
        
        {/* Stats */}
        {(contextUpdates > 0 || sensorData > 0) && (
          <div className="flex gap-3 mt-2 text-xs text-muted-foreground">
            {contextUpdates > 0 && (
              <span className="flex items-center gap-1">
                <div className="w-2 h-2 bg-blue-500 rounded-full" />
                {contextUpdates} context
              </span>
            )}
            {sensorData > 0 && (
              <span className="flex items-center gap-1">
                <div className="w-2 h-2 bg-purple-500 rounded-full" />
                {sensorData} sensor
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// Minimalist floating dot indicator
export function TrackingDot({ 
  isActive, 
  className,
  position = 'top-right'
}: Pick<TrackingIndicatorProps, 'isActive' | 'className' | 'position'>) {
  const [pulse, setPulse] = useState(false)
  
  useEffect(() => {
    if (!isActive) return
    
    const interval = setInterval(() => {
      setPulse(true)
      setTimeout(() => setPulse(false), 1000)
    }, 3000)
    
    return () => clearInterval(interval)
  }, [isActive])
  
  const positionClasses = {
    'top-left': 'top-4 left-4',
    'top-right': 'top-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'bottom-right': 'bottom-4 right-4'
  }
  
  if (!isActive) return null
  
  return (
    <div className={cn(
      "fixed z-50 pointer-events-none",
      positionClasses[position],
      className
    )}>
      <div className="relative">
        {pulse && (
          <div className="absolute inset-0 w-4 h-4 bg-green-500 rounded-full animate-ping" />
        )}
        <div className="relative w-4 h-4 bg-green-500 rounded-full shadow-lg" />
      </div>
    </div>
  )
}

// Live data stream visualization
export function TrackingStream({ 
  isActive,
  dataRate = 0, // messages per second
  className,
  position = 'top-right'
}: TrackingIndicatorProps & { dataRate?: number }) {
  const [particles, setParticles] = useState<{ id: number; progress: number }[]>([])
  
  useEffect(() => {
    if (!isActive || dataRate === 0) return
    
    const interval = setInterval(() => {
      setParticles(prev => {
        const updated = prev
          .map(p => ({ ...p, progress: p.progress + 0.05 }))
          .filter(p => p.progress < 1)
        
        // Add new particle based on data rate
        if (Math.random() < dataRate / 60) {
          updated.push({ id: Date.now(), progress: 0 })
        }
        
        return updated
      })
    }, 16) // 60fps
    
    return () => clearInterval(interval)
  }, [isActive, dataRate])
  
  const positionClasses = {
    'top-left': 'top-4 left-4',
    'top-right': 'top-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'bottom-right': 'bottom-4 right-4'
  }
  
  if (!isActive) return null
  
  return (
    <div className={cn(
      "fixed z-50 pointer-events-none",
      positionClasses[position],
      className
    )}>
      <div className="relative w-32 h-1 bg-gray-800 rounded-full overflow-hidden">
        {particles.map(particle => (
          <div
            key={particle.id}
            className="absolute w-4 h-1 bg-gradient-to-r from-green-500 to-transparent"
            style={{
              left: `${particle.progress * 100}%`,
              opacity: 1 - particle.progress * 0.5
            }}
          />
        ))}
      </div>
    </div>
  )
}