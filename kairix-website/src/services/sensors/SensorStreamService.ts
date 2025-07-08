import type {
  OrientationData,
  MotionData,
  SensorStreamConfig,
  SensorStreamMessage,
  SensorPayload,
  SensorStreamState,
  MotionPattern,
  AmbientLightData
} from '@/types/sensors'

export class SensorStreamService {
  private static instance: SensorStreamService
  private ws?: WebSocket
  private config: SensorStreamConfig
  private state: SensorStreamState
  private sessionId: string
  private sensorHandlers: Map<string, any> = new Map()
  private messageBuffer: SensorStreamMessage[] = []
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  
  private constructor() {
    this.sessionId = this.generateSessionId()
    
    this.config = {
      sensors: {
        motion: true,
        accelerometer: true,
        gyroscope: true,
        magnetometer: false,
        orientation: true,
        proximity: false,
        ambientLight: false,
        pressure: false,
        humidity: false,
        temperature: false
      },
      sampleRates: {
        motion: 60, // 60Hz for smooth motion tracking
        environmental: 1 // 1Hz for environmental sensors
      },
      processing: {
        detectPatterns: true,
        detectGestures: true,
        smoothing: true,
        calibrate: true
      },
      transmission: {
        mode: 'adaptive', // Switch between realtime and batch based on activity
        batchSize: 10,
        batchInterval: 100,
        compression: true,
        throttleRate: 100 // max 100 messages per second
      },
      powerMode: 'balanced'
    }
    
    this.state = {
      connected: false,
      streaming: false,
      lastUpdate: 0,
      errorCount: 0,
      bufferedMessages: 0,
      sensors: {}
    }
  }
  
  static getInstance(): SensorStreamService {
    if (!SensorStreamService.instance) {
      SensorStreamService.instance = new SensorStreamService()
    }
    return SensorStreamService.instance
  }
  
  private generateSessionId(): string {
    return `sensor-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }
  
  async connect(): Promise<void> {
    // Sensor WebSocket disabled - backend doesn't support it
    console.log('Sensor WebSocket disabled - not implemented on backend')
    return
  }
  
  private buildWebSocketUrl(): string {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://')
    const apiKey = localStorage.getItem('apiKey') || ''
    
    return `${wsUrl}/ws/sensors?session_id=${this.sessionId}&api_key=${encodeURIComponent(apiKey)}`
  }
  
  private sendConfiguration(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return
    
    this.ws.send(JSON.stringify({
      type: 'config_update',
      sessionId: this.sessionId,
      deviceId: this.getDeviceId(),
      timestamp: Date.now(),
      data: {
        type: 'config',
        config: this.config
      }
    }))
  }
  
  private getDeviceId(): string {
    let deviceId = localStorage.getItem('deviceId')
    if (!deviceId) {
      deviceId = `${navigator.platform}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('deviceId', deviceId)
    }
    return deviceId
  }
  
  async startStreaming(): Promise<void> {
    if (!this.state.connected) {
      await this.connect()
    }
    
    this.state.streaming = true
    
    // Initialize sensors based on configuration
    if (this.config.sensors.motion) {
      await this.initializeMotionSensors()
    }
    
    if (this.config.sensors.orientation) {
      await this.initializeOrientationSensor()
    }
    
    if (this.config.sensors.ambientLight) {
      await this.initializeAmbientLightSensor()
    }
    
    // Start batch transmission if configured
    if (this.config.transmission.mode === 'batch') {
      this.startBatchTransmission()
    }
  }
  
  private async initializeMotionSensors(): Promise<void> {
    // Check if DeviceMotion is available
    if (!('DeviceMotionEvent' in window)) {
      console.warn('DeviceMotion not available')
      return
    }
    
    // Request permission on iOS
    if (typeof (DeviceMotionEvent as any).requestPermission === 'function') {
      try {
        const permission = await (DeviceMotionEvent as any).requestPermission()
        if (permission !== 'granted') {
          console.warn('Motion permission denied')
          return
        }
      } catch (error) {
        console.error('Error requesting motion permission:', error)
        return
      }
    }
    
    const motionHandler = (event: DeviceMotionEvent) => {
      const motionData: MotionData = {
        acceleration: {
          x: event.acceleration?.x || 0,
          y: event.acceleration?.y || 0,
          z: event.acceleration?.z || 0,
          timestamp: Date.now(),
          includesGravity: false
        },
        accelerationIncludingGravity: {
          x: event.accelerationIncludingGravity?.x || 0,
          y: event.accelerationIncludingGravity?.y || 0,
          z: event.accelerationIncludingGravity?.z || 0,
          timestamp: Date.now(),
          includesGravity: true
        },
        rotationRate: {
          alpha: event.rotationRate?.alpha || 0,
          beta: event.rotationRate?.beta || 0,
          gamma: event.rotationRate?.gamma || 0,
          timestamp: Date.now()
        },
        orientation: {
          alpha: 0, // Will be filled by orientation event
          beta: 0,
          gamma: 0,
          absolute: false,
          timestamp: Date.now()
        },
        interval: event.interval || 16,
        timestamp: Date.now()
      }
      
      // Apply smoothing if enabled
      if (this.config.processing.smoothing) {
        this.smoothMotionData(motionData)
      }
      
      // Detect patterns if enabled
      if (this.config.processing.detectPatterns) {
        this.detectMotionPatterns(motionData)
      }
      
      // Send or buffer the data
      this.sendSensorData({ type: 'motion', data: motionData })
    }
    
    window.addEventListener('devicemotion', motionHandler)
    this.sensorHandlers.set('motion', motionHandler)
    
    this.state.sensors.motion = {
      available: true,
      active: true,
      lastReading: Date.now(),
      errorRate: 0
    }
  }
  
  private async initializeOrientationSensor(): Promise<void> {
    // Check if DeviceOrientation is available
    if (!('DeviceOrientationEvent' in window)) {
      console.warn('DeviceOrientation not available')
      return
    }
    
    // Request permission on iOS
    if (typeof (DeviceOrientationEvent as any).requestPermission === 'function') {
      try {
        const permission = await (DeviceOrientationEvent as any).requestPermission()
        if (permission !== 'granted') {
          console.warn('Orientation permission denied')
          return
        }
      } catch (error) {
        console.error('Error requesting orientation permission:', error)
        return
      }
    }
    
    const orientationHandler = (event: DeviceOrientationEvent) => {
      const orientationData: OrientationData = {
        alpha: event.alpha || 0,
        beta: event.beta || 0,
        gamma: event.gamma || 0,
        absolute: event.absolute || false,
        timestamp: Date.now()
      }
      
      // Detect gestures if enabled
      if (this.config.processing.detectGestures) {
        this.detectGestures(orientationData)
      }
      
      this.sendSensorData({ type: 'orientation', data: orientationData })
    }
    
    window.addEventListener('deviceorientation', orientationHandler)
    this.sensorHandlers.set('orientation', orientationHandler)
    
    this.state.sensors.orientation = {
      available: true,
      active: true,
      lastReading: Date.now(),
      errorRate: 0
    }
  }
  
  private async initializeAmbientLightSensor(): Promise<void> {
    if (!('AmbientLightSensor' in window)) {
      console.warn('AmbientLightSensor not available')
      return
    }
    
    try {
      const sensor = new (window as any).AmbientLightSensor()
      
      sensor.addEventListener('reading', () => {
        const lightData: AmbientLightData = {
          illuminance: sensor.illuminance,
          timestamp: Date.now(),
          lightCondition: this.classifyLightLevel(sensor.illuminance) as AmbientLightData['lightCondition']
        }
        
        this.sendSensorData({ type: 'ambient_light', data: lightData })
      })
      
      sensor.addEventListener('error', (event: any) => {
        console.error('Ambient light sensor error:', event.error)
      })
      
      sensor.start()
      this.sensorHandlers.set('ambientLight', sensor)
      
      this.state.sensors.ambientLight = {
        available: true,
        active: true,
        lastReading: Date.now(),
        errorRate: 0
      }
    } catch (error) {
      console.error('Failed to initialize ambient light sensor:', error)
    }
  }
  
  private classifyLightLevel(lux: number): 'dark' | 'dim' | 'normal' | 'bright' | 'very-bright' {
    if (lux < 50) return 'dark'
    if (lux < 200) return 'dim'
    if (lux < 400) return 'normal'
    if (lux < 1000) return 'bright'
    return 'very-bright'
  }
  
  private smoothMotionData(_data: MotionData): void {
    // Simple exponential smoothing
    // Would implement more sophisticated filtering in production
  }
  
  private detectMotionPatterns(data: MotionData): void {
    // Analyze acceleration patterns to detect walking, running, etc.
    const magnitude = Math.sqrt(
      data.acceleration.x ** 2 + 
      data.acceleration.y ** 2 + 
      data.acceleration.z ** 2
    )
    
    // Simple pattern detection - would use ML model in production
    let pattern: MotionPattern | null = null
    
    if (magnitude < 0.5) {
      pattern = {
        type: 'stationary',
        confidence: 0.9,
        timestamp: Date.now()
      }
    } else if (magnitude < 2) {
      pattern = {
        type: 'walking',
        confidence: 0.7,
        details: {
          speed: magnitude * 1.4, // rough estimation
          cadence: 100 // would calculate from frequency analysis
        },
        timestamp: Date.now()
      }
    } else if (magnitude < 5) {
      pattern = {
        type: 'running',
        confidence: 0.7,
        details: {
          speed: magnitude * 2.5,
          cadence: 160
        },
        timestamp: Date.now()
      }
    }
    
    if (pattern) {
      this.sendSensorData({ type: 'pattern', data: pattern })
    }
  }
  
  private detectGestures(_data: OrientationData): void {
    // Simple gesture detection based on orientation changes
    // Would use more sophisticated algorithm in production
  }
  
  private sendSensorData(payload: SensorPayload): void {
    const message: SensorStreamMessage = {
      type: 'sensor_data',
      sessionId: this.sessionId,
      deviceId: this.getDeviceId(),
      timestamp: Date.now(),
      data: payload
    }
    
    // Check throttling
    if (this.shouldThrottle()) {
      this.messageBuffer.push(message)
      return
    }
    
    // Send based on transmission mode
    switch (this.config.transmission.mode) {
      case 'realtime':
        this.sendMessage(message)
        break
        
      case 'batch':
        this.messageBuffer.push(message)
        if (this.messageBuffer.length >= this.config.transmission.batchSize!) {
          this.flushMessageBuffer()
        }
        break
        
      case 'adaptive':
        // Switch between realtime and batch based on activity
        if (payload.type === 'pattern' || payload.type === 'gesture') {
          this.sendMessage(message) // Important events go immediately
        } else {
          this.messageBuffer.push(message)
        }
        break
    }
    
    this.state.lastUpdate = Date.now()
  }
  
  private shouldThrottle(): boolean {
    // Implement throttling logic
    return false
  }
  
  private sendMessage(message: SensorStreamMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.messageBuffer.push(message)
      return
    }
    
    try {
      if (this.config.transmission.compression) {
        // Would implement compression here
        this.ws.send(JSON.stringify(message))
      } else {
        this.ws.send(JSON.stringify(message))
      }
    } catch (error) {
      console.error('Failed to send sensor data:', error)
      this.messageBuffer.push(message)
    }
  }
  
  private flushMessageBuffer(): void {
    if (this.messageBuffer.length === 0) return
    
    if (this.config.transmission.mode === 'batch' || this.messageBuffer.length > 1) {
      // Send as batch
      const batchMessage: SensorStreamMessage = {
        type: 'sensor_data',
        sessionId: this.sessionId,
        deviceId: this.getDeviceId(),
        timestamp: Date.now(),
        data: {
          type: 'batch',
          data: this.messageBuffer.map(m => m.data)
        }
      }
      
      this.sendMessage(batchMessage)
    } else {
      // Send individually
      this.messageBuffer.forEach(message => this.sendMessage(message))
    }
    
    this.messageBuffer = []
    this.state.bufferedMessages = 0
  }
  
  private startBatchTransmission(): void {
    setInterval(() => {
      this.flushMessageBuffer()
    }, this.config.transmission.batchInterval || 100)
  }
  
  private handleServerMessage(message: any): void {
    switch (message.type) {
      case 'config_update':
        this.updateConfig(message.config)
        break
        
      case 'pattern_feedback':
        // Server might send feedback on pattern detection accuracy
        console.log('Pattern feedback:', message)
        break
        
      case 'error':
        console.error('Server error:', message.error)
        break
    }
  }
  
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }
    
    this.reconnectAttempts++
    
    setTimeout(() => {
      console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts}`)
      this.connect()
    }, this.reconnectDelay * this.reconnectAttempts)
  }
  
  updateConfig(config: Partial<SensorStreamConfig>): void {
    this.config = { ...this.config, ...config }
    
    // Restart sensors if configuration changed
    if (this.state.streaming) {
      this.stopStreaming()
      this.startStreaming()
    }
  }
  
  stopStreaming(): void {
    this.state.streaming = false
    
    // Remove all event listeners
    this.sensorHandlers.forEach((handler, type) => {
      switch (type) {
        case 'motion':
          window.removeEventListener('devicemotion', handler)
          break
        case 'orientation':
          window.removeEventListener('deviceorientation', handler)
          break
        case 'ambientLight':
          if (handler.stop) handler.stop()
          break
      }
    })
    
    this.sensorHandlers.clear()
    
    // Flush any remaining messages
    this.flushMessageBuffer()
  }
  
  disconnect(): void {
    this.stopStreaming()
    
    if (this.ws) {
      this.ws.close()
      this.ws = undefined
    }
    
    this.state.connected = false
  }
  
  getState(): SensorStreamState {
    return { ...this.state }
  }
}