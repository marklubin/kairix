import { useState, useEffect, useCallback } from 'react'
import { ContextService } from '@/services/context/ContextService'
import { SensorStreamService } from '@/services/sensors/SensorStreamService'
import type { ContextConfig, ContextUpdate } from '@/types/context'
import type { SensorStreamConfig, SensorStreamState } from '@/types/sensors'

interface UseContextualAwarenessOptions {
  enableContext?: boolean
  enableSensors?: boolean
  contextConfig?: Partial<ContextConfig>
  sensorConfig?: Partial<SensorStreamConfig>
  onContextUpdate?: (update: ContextUpdate) => void
  onSensorStateChange?: (state: SensorStreamState) => void
}

interface UseContextualAwarenessReturn {
  // Context
  contextEnabled: boolean
  lastContextUpdate?: ContextUpdate
  triggerContextUpdate: (reason: string, priority?: 'low' | 'normal' | 'high') => Promise<void>
  updateContextConfig: (config: Partial<ContextConfig>) => void
  
  // Sensors
  sensorsEnabled: boolean
  sensorState: SensorStreamState
  startSensorStream: () => Promise<void>
  stopSensorStream: () => void
  updateSensorConfig: (config: Partial<SensorStreamConfig>) => void
  
  // Combined
  isActive: boolean
  hasPermissions: boolean
  errors: string[]
}

export function useContextualAwareness(options: UseContextualAwarenessOptions = {}): UseContextualAwarenessReturn {
  const {
    enableContext = true,
    enableSensors = false, // Disabled by default as it requires permissions
    contextConfig,
    sensorConfig,
    onContextUpdate,
    onSensorStateChange
  } = options
  
  const [contextEnabled] = useState(enableContext)
  const [sensorsEnabled, setSensorsEnabled] = useState(enableSensors)
  const [lastContextUpdate, setLastContextUpdate] = useState<ContextUpdate>()
  const [sensorState, setSensorState] = useState<SensorStreamState>({
    connected: false,
    streaming: false,
    lastUpdate: 0,
    errorCount: 0,
    bufferedMessages: 0,
    sensors: {}
  })
  const [hasPermissions, setHasPermissions] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  
  const contextService = ContextService.getInstance()
  const sensorService = SensorStreamService.getInstance()
  
  // Initialize context service
  useEffect(() => {
    if (!contextEnabled) return
    
    const initContext = async () => {
      try {
        await contextService.initialize(contextConfig)
        setHasPermissions(true)
        
        // Collect initial context immediately
        const initialUpdate = await contextService.collectAllContext()
        setLastContextUpdate(initialUpdate)
        if (onContextUpdate) {
          onContextUpdate(initialUpdate)
        }
        
        // Set up periodic context collection
        const interval = setInterval(async () => {
          const update = await contextService.collectAllContext()
          setLastContextUpdate(update)
          if (onContextUpdate) {
            onContextUpdate(update)
          }
        }, contextConfig?.updateInterval || 30000)
        
        return () => {
          clearInterval(interval)
          contextService.stop()
        }
      } catch (error) {
        console.error('Failed to initialize context service:', error)
        setErrors(prev => [...prev, `Context initialization failed: ${error}`])
      }
    }
    
    initContext()
  }, [contextEnabled, contextConfig])
  
  // Initialize sensor service
  useEffect(() => {
    if (!sensorsEnabled) return
    
    const initSensors = async () => {
      try {
        if (sensorConfig) {
          sensorService.updateConfig(sensorConfig)
        }
        
        // Monitor sensor state
        const stateInterval = setInterval(() => {
          const state = sensorService.getState()
          setSensorState(state)
          if (onSensorStateChange) {
            onSensorStateChange(state)
          }
        }, 1000)
        
        return () => {
          clearInterval(stateInterval)
          sensorService.disconnect()
        }
      } catch (error) {
        console.error('Failed to initialize sensor service:', error)
        setErrors(prev => [...prev, `Sensor initialization failed: ${error}`])
      }
    }
    
    initSensors()
  }, [sensorsEnabled, sensorConfig])
  
  const triggerContextUpdate = useCallback(
    async (reason: string, priority: 'low' | 'normal' | 'high' = 'normal') => {
      if (!contextEnabled) {
        console.warn('Context service is not enabled')
        return
      }
      
      try {
        await contextService.triggerContextUpdate(reason, priority)
      } catch (error) {
        console.error('Failed to trigger context update:', error)
        setErrors(prev => [...prev, `Context update failed: ${error}`])
      }
    },
    [contextEnabled]
  )
  
  const updateContextConfig = useCallback((config: Partial<ContextConfig>) => {
    contextService.updateConfig(config)
  }, [])
  
  const startSensorStream = useCallback(async () => {
    if (!sensorsEnabled) {
      console.warn('Sensor service is not enabled')
      return
    }
    
    try {
      await sensorService.startStreaming()
      setSensorsEnabled(true)
    } catch (error) {
      console.error('Failed to start sensor stream:', error)
      setErrors(prev => [...prev, `Sensor stream failed: ${error}`])
    }
  }, [sensorsEnabled])
  
  const stopSensorStream = useCallback(() => {
    sensorService.stopStreaming()
  }, [])
  
  const updateSensorConfig = useCallback((config: Partial<SensorStreamConfig>) => {
    sensorService.updateConfig(config)
  }, [])
  
  return {
    // Context
    contextEnabled,
    lastContextUpdate,
    triggerContextUpdate,
    updateContextConfig,
    
    // Sensors
    sensorsEnabled,
    sensorState,
    startSensorStream,
    stopSensorStream,
    updateSensorConfig,
    
    // Combined
    isActive: contextEnabled || (sensorsEnabled && sensorState.streaming),
    hasPermissions,
    errors
  }
}