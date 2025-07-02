import { useEffect, useState } from 'react'
import { useContextualAwareness } from '@/hooks/useContextualAwareness'
import { cn } from '@/lib/utils'

export function ContextStatus() {
  const [hovering, setHovering] = useState(false)
  const [lastUpdateTime, setLastUpdateTime] = useState<number | null>(null)
  const [nextUpdateTime, setNextUpdateTime] = useState<number | null>(null)
  const [currentTime, setCurrentTime] = useState(Date.now())
  
  const {
    lastContextUpdate,
    errors,
    isActive
  } = useContextualAwareness({
    enableContext: true,
    enableSensors: false
  })
  
  // Update current time every second for relative time display, but only when hovering
  useEffect(() => {
    if (hovering) {
      const interval = setInterval(() => setCurrentTime(Date.now()), 1000)
      return () => clearInterval(interval)
    }
  }, [hovering])
  
  // Track update times
  useEffect(() => {
    if (lastContextUpdate) {
      setLastUpdateTime(lastContextUpdate.timestamp)
      // Next update in 30 seconds (or whatever the interval is)
      setNextUpdateTime(lastContextUpdate.timestamp + 30000)
    }
  }, [lastContextUpdate])
  
  const formatRelativeTime = (timestamp: number) => {
    const diff = Math.floor((currentTime - timestamp) / 1000)
    if (diff < 60) return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    return `${Math.floor(diff / 3600)}h ago`
  }
  
  const formatTimeUntil = (timestamp: number) => {
    const diff = Math.floor((timestamp - currentTime) / 1000)
    if (diff < 0) return 'now'
    if (diff < 60) return `in ${diff}s`
    return `in ${Math.floor(diff / 60)}m`
  }
  
  const hasErrors = errors.length > 0
  const lastError = errors[errors.length - 1]
  
  return (
    <div
      className={cn(
        "fixed right-0 top-1/2 -translate-y-1/2 z-50 transition-all duration-300",
        hovering ? "translate-x-0" : "translate-x-[calc(100%-12px)]"
      )}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
    >
      <div className="bg-background/95 backdrop-blur-md border border-r-0 rounded-l-lg shadow-lg holographic">
        {/* Tab indicator */}
        <div className="absolute -left-3 top-1/2 -translate-y-1/2 w-3 h-16 bg-background/95 backdrop-blur-md border border-r-0 rounded-l-md flex items-center justify-center">
          <div className={cn(
            "w-1.5 h-1.5 rounded-full transition-all duration-300",
            hasErrors ? "bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.7)]" : 
            (isActive ? "bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.7)] animate-pulse" : 
            "bg-gray-400")
          )} />
        </div>
        
        {/* Content */}
        <div className="p-4 pl-6 min-w-[280px]">
          <div className="text-xs font-medium mb-3 flex items-center gap-2">
            <div className={cn(
              "w-2 h-2 rounded-full transition-all duration-300",
              hasErrors ? "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.7)]" : 
              (isActive ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.7)] animate-pulse" : 
              "bg-gray-400")
            )} />
            <span className="gradient-text font-mono tracking-wider">CONTEXT STREAM</span>
          </div>
          
          {hasErrors ? (
            <div className="space-y-2">
              <div className="text-xs font-mono text-red-500 font-semibold uppercase tracking-wide">System Error</div>
              <div className="text-xs text-red-400 break-words max-w-[240px] font-mono">
                {lastError}
              </div>
              {lastUpdateTime && (
                <div className="text-xs text-muted-foreground font-mono">
                  Last successful: <span className="text-primary">{formatRelativeTime(lastUpdateTime)}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              {lastUpdateTime ? (
                <>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground font-mono">LAST SYNC:</span>
                    <span className="text-primary font-semibold font-mono">{formatRelativeTime(lastUpdateTime)}</span>
                  </div>
                  {nextUpdateTime && (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-muted-foreground font-mono">NEXT SYNC:</span>
                      <span className="text-secondary font-semibold font-mono">{formatTimeUntil(nextUpdateTime)}</span>
                    </div>
                  )}
                  {lastContextUpdate?.contexts.geolocation && (
                    <div className="mt-3 pt-3 border-t border-border/50">
                      <div className="text-xs font-mono text-muted-foreground mb-1">COORDINATES</div>
                      <div className="text-xs font-mono text-primary">
                        {lastContextUpdate.contexts.geolocation.latitude.toFixed(4)}° N, {Math.abs(lastContextUpdate.contexts.geolocation.longitude).toFixed(4)}° W
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-xs text-muted-foreground font-mono animate-pulse">
                  INITIALIZING STREAM...
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}