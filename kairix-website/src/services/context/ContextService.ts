import type { 
  GeolocationContext, 
  DeviceContext, 
  EnvironmentContext, 
  ActivityContext,
  ContextUpdate,
  ContextConfig,
  ContextPermissions
} from '@/types/context'
import { ContextDebugStore } from './ContextDebugStore'

export class ContextService {
  private static instance: ContextService
  private static initialized = false
  private config: ContextConfig
  private permissions: ContextPermissions = {
    geolocation: 'prompt',
    motion: 'prompt',
    camera: 'prompt',
    microphone: 'prompt',
    notifications: 'prompt'
  }
  
  private updateInterval?: number
  private watchId?: number
  private contextApiUrl: string
  private sessionId: string
  private lastSentUpdate: string | null = null
  
  private constructor() {
    // Use the same backend API that's already running
    this.contextApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    this.sessionId = this.generateSessionId()
    
    console.log('ContextService initialized with:', {
      apiUrl: this.contextApiUrl,
      sessionId: this.sessionId
    })
    
    this.config = {
      enabledContexts: {
        geolocation: true,
        device: true,
        environment: true,
        activity: true,
        calendar: false,
        media: false
      },
      updateInterval: 30000, // 30 seconds
      significantChangeThresholds: {
        location: 50, // meters
        activity: 0.2,
        light: 100
      },
      anonymizeData: false,
      retentionPeriod: 86400000, // 24 hours
      shareWithThirdParties: false
    }
  }
  
  static getInstance(): ContextService {
    if (!ContextService.instance) {
      ContextService.instance = new ContextService()
    }
    return ContextService.instance
  }
  
  
  async initialize(config?: Partial<ContextConfig>): Promise<void> {
    if (ContextService.initialized) {
      console.log('ContextService already initialized, skipping')
      return
    }
    
    if (config) {
      this.config = { ...this.config, ...config }
    }
    
    // Check permissions
    await this.checkPermissions()
    
    // Start periodic updates
    if (this.config.updateInterval > 0) {
      this.startPeriodicUpdates()
    }
    
    // Start watching for significant changes
    this.watchSignificantChanges()
    
    ContextService.initialized = true
  }
  
  private async checkPermissions(): Promise<void> {
    // Check geolocation permission
    if ('permissions' in navigator) {
      try {
        const geoPermission = await navigator.permissions.query({ name: 'geolocation' })
        this.permissions.geolocation = geoPermission.state as any
        
        geoPermission.addEventListener('change', () => {
          this.permissions.geolocation = geoPermission.state as any
        })
      } catch (e) {
        console.warn('Could not check geolocation permission:', e)
      }
    }
  }
  
  private generateSessionId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }
  
  async collectGeolocation(): Promise<GeolocationContext | null> {
    if (!this.config.enabledContexts.geolocation || this.permissions.geolocation === 'denied') {
      return null
    }
    
    try {
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: false,
          timeout: 2000,
          maximumAge: 30000 // Use cached position up to 30 seconds old
        })
      })
      
      return {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
        altitude: position.coords.altitude,
        altitudeAccuracy: position.coords.altitudeAccuracy,
        heading: position.coords.heading,
        speed: position.coords.speed,
        timestamp: position.timestamp
      }
    } catch (error) {
      console.error('Failed to get geolocation:', error)
      return null
    }
  }
  
  collectDevice(): DeviceContext {
    const getConnectionType = (): string => {
      const connection = (navigator as any).connection || (navigator as any).mozConnection || (navigator as any).webkitConnection
      if (!connection) return 'unknown'
      
      if (connection.type) return connection.type
      if (connection.effectiveType) return connection.effectiveType
      return 'unknown'
    }
    
    const getMemoryInfo = () => {
      const memory = (performance as any).memory
      if (!memory) return undefined
      
      return {
        deviceMemory: (navigator as any).deviceMemory,
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit
      }
    }
    
    return {
      platform: navigator.platform,
      userAgent: navigator.userAgent,
      language: navigator.language,
      languages: [...navigator.languages],
      screenResolution: {
        width: window.screen.width,
        height: window.screen.height,
        pixelRatio: window.devicePixelRatio
      },
      touchEnabled: 'ontouchstart' in window,
      onLine: navigator.onLine,
      connectionType: getConnectionType(),
      memory: getMemoryInfo()
    }
  }
  
  collectEnvironment(): EnvironmentContext {
    const isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches
    
    return {
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      timezoneOffset: new Date().getTimezoneOffset(),
      localTime: new Date().toISOString(),
      isDarkMode
    }
  }
  
  collectActivity(): ActivityContext {
    const getIdleTime = (): number => {
      // Simple idle detection - would need more sophisticated implementation
      return 0
    }
    
    // Initialize session start if not exists
    if (!sessionStorage.getItem('sessionStart')) {
      sessionStorage.setItem('sessionStart', Date.now().toString())
    }
    
    return {
      currentUrl: window.location.href,
      pageTitle: document.title,
      referrer: document.referrer || '',
      sessionDuration: Date.now() - parseInt(sessionStorage.getItem('sessionStart') || Date.now().toString()),
      lastActiveTimestamp: Date.now(),
      idleTime: getIdleTime()
    }
  }
  
  async collectAllContext(): Promise<ContextUpdate> {
    const contexts: any = {}
    
    if (this.config.enabledContexts.geolocation) {
      contexts.geolocation = await this.collectGeolocation()
    }
    
    if (this.config.enabledContexts.device) {
      contexts.device = this.collectDevice()
    }
    
    if (this.config.enabledContexts.environment) {
      contexts.environment = this.collectEnvironment()
    }
    
    if (this.config.enabledContexts.activity) {
      contexts.activity = this.collectActivity()
    }
    
    return {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      contexts,
      trigger: 'periodic',
      priority: 'normal'
    }
  }
  
  async sendContextUpdate(update: ContextUpdate): Promise<void> {
    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        'X-API-Key': localStorage.getItem('apiKey') || 'test-api-key-12345'
      }
      
      // Map client context structure to server's expected format
      const requestBody: any = {
        timestamp: update.timestamp,
        session_id: this.sessionId,
        device_id: this.getDeviceId()
      }
      
      // Map geolocation data
      if (update.contexts.geolocation) {
        requestBody.geolocation = {
          latitude: update.contexts.geolocation.latitude,
          longitude: update.contexts.geolocation.longitude,
          accuracy: update.contexts.geolocation.accuracy,
          altitude: update.contexts.geolocation.altitude,
          altitude_accuracy: update.contexts.geolocation.altitudeAccuracy,
          heading: update.contexts.geolocation.heading,
          speed: update.contexts.geolocation.speed,
          timestamp: update.contexts.geolocation.timestamp,
          address: update.contexts.geolocation.address
        }
      }
      
      // Map device data
      if (update.contexts.device) {
        requestBody.device = {
          platform: update.contexts.device.platform,
          os_version: update.contexts.device.userAgent, // Using userAgent as os_version
          browser: navigator.userAgent.split(' ').pop(), // Extract browser info
          screen_width: update.contexts.device.screenResolution?.width,
          screen_height: update.contexts.device.screenResolution?.height,
          pixel_ratio: update.contexts.device.screenResolution?.pixelRatio,
          language: update.contexts.device.language,
          timezone: update.contexts.environment?.timezone, // This might be undefined
          battery_level: update.contexts.device.battery?.level,
          battery_charging: update.contexts.device.battery?.charging,
          network_type: update.contexts.device.connectionType === 'wifi' || 
                       update.contexts.device.connectionType === 'cellular' || 
                       update.contexts.device.connectionType === 'ethernet' ? 
                       update.contexts.device.connectionType : 'none',
          connection_speed: ['slow-2g', '2g', '3g', '4g', '5g'].includes(update.contexts.device.effectiveConnectionType || '') 
                           ? update.contexts.device.effectiveConnectionType 
                           : undefined
        }
      }
      
      // Map activity data
      if (update.contexts.activity) {
        requestBody.activity = {
          current_url: update.contexts.activity.currentUrl,
          page_title: update.contexts.activity.pageTitle,
          session_duration: update.contexts.activity.sessionDuration,
          idle_time: update.contexts.activity.idleTime,
          activity_type: update.contexts.activity.activityType,
          confidence: update.contexts.activity.confidence,
          is_active_tab: document.hasFocus(),
          media_playing: update.contexts.media?.playingMedia?.state === 'playing'
        }
      }
      
      // Map environment data
      if (update.contexts.environment) {
        requestBody.environment = {
          ambient_light: update.contexts.environment.ambientLight,
          ambient_noise: update.contexts.environment.ambientNoise,
          temperature: update.contexts.environment.weather?.temperature,
          humidity: update.contexts.environment.weather?.humidity,
          pressure: update.contexts.environment.weather?.pressure,
          weather: update.contexts.environment.weather ? {
            condition: update.contexts.environment.weather.description,
            temperature: update.contexts.environment.weather.temperature,
            feels_like: update.contexts.environment.weather.feelsLike,
            wind_speed: update.contexts.environment.weather.windSpeed,
            wind_direction: update.contexts.environment.weather.windDirection
          } : undefined
        }
      }
      
      // Add custom data if present
      if (update.contexts.custom) {
        requestBody.custom = update.contexts.custom
      }
      
      // Create a normalized version for comparison (exclude timestamp and session_duration)
      const normalizedForComparison = {
        ...requestBody,
        timestamp: 0, // Ignore timestamp for comparison
        activity: requestBody.activity ? {
          ...requestBody.activity,
          session_duration: 0, // Ignore session duration
          idle_time: 0 // Ignore idle time
        } : undefined
      }
      
      const currentUpdateString = JSON.stringify(normalizedForComparison)
      
      // Check if the data has changed
      if (this.lastSentUpdate === currentUpdateString) {
        console.log('Context update skipped - no changes detected')
        return
      }
      
      console.log('Sending context update - changes detected')
      
      // Capture request in debug store
      const debugStore = ContextDebugStore.getInstance()
      const requestId = debugStore.addRequest({
        method: 'POST',
        url: `${this.contextApiUrl}/context/update`,
        headers,
        body: requestBody
      })
      
      const response = await fetch(`${this.contextApiUrl}/context/update`, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody)
      })
      
      // Store the normalized version after successful send
      if (response.ok) {
        this.lastSentUpdate = currentUpdateString
      }
      
      // Capture response in debug store
      let responseBody: any
      const responseText = await response.text()
      
      try {
        responseBody = responseText ? JSON.parse(responseText) : null
      } catch {
        responseBody = responseText
      }
      
      debugStore.updateRequestResponse(requestId, {
        status: response.status,
        statusText: response.statusText,
        body: responseBody,
        timestamp: Date.now()
      })
      
      if (!response.ok) {
        console.error('Context update failed:', {
          status: response.status,
          statusText: response.statusText,
          body: responseBody
        })
        throw new Error(`Failed to send context update: ${response.status} ${response.statusText} - ${responseText}`)
      }
      
      console.log('Context update sent:', responseBody)
      
      // Handle any recommendations from the server
      if (responseBody?.recommendations) {
        this.handleRecommendations(responseBody.recommendations)
      }
    } catch (error) {
      console.error('Failed to send context update:', error)
    }
  }
  
  private getDeviceId(): string {
    let deviceId = localStorage.getItem('deviceId')
    if (!deviceId) {
      deviceId = `${navigator.platform}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('deviceId', deviceId)
    }
    return deviceId
  }
  
  private handleRecommendations(recommendations: string[]): void {
    // Handle contextual recommendations from the server
    console.log('Received recommendations:', recommendations)
    // Could dispatch events or update UI based on recommendations
  }
  
  private startPeriodicUpdates(): void {
    // Clear any existing interval
    if (this.updateInterval) {
      clearInterval(this.updateInterval)
    }
    
    // Send initial update
    this.sendUpdate()
    
    // Set up periodic updates
    this.updateInterval = window.setInterval(() => {
      this.sendUpdate()
    }, this.config.updateInterval)
  }
  
  private async sendUpdate(): Promise<void> {
    const update = await this.collectAllContext()
    await this.sendContextUpdate(update)
  }
  
  private watchSignificantChanges(): void {
    // Disabled geolocation watching - just use periodic updates
    
    // Watch for online/offline changes
    window.addEventListener('online', () => this.handleConnectivityChange(true))
    window.addEventListener('offline', () => this.handleConnectivityChange(false))
    
    // Watch for visibility changes
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        this.sendUpdate()
      }
    })
  }
  
  private async handleConnectivityChange(_online: boolean): Promise<void> {
    const update = await this.collectAllContext()
    update.trigger = 'significant_change'
    update.priority = 'high'
    await this.sendContextUpdate(update)
  }
  
  // Manual trigger for important context changes
  async triggerContextUpdate(_reason: string, priority: 'low' | 'normal' | 'high' = 'normal'): Promise<void> {
    const update = await this.collectAllContext()
    update.trigger = 'manual'
    update.priority = priority
    await this.sendContextUpdate(update)
  }
  
  updateConfig(config: Partial<ContextConfig>): void {
    this.config = { ...this.config, ...config }
    
    // Restart periodic updates if interval changed
    if (config.updateInterval !== undefined) {
      this.startPeriodicUpdates()
    }
  }
  
  stop(): void {
    if (this.updateInterval) {
      clearInterval(this.updateInterval)
    }
    
    if (this.watchId !== undefined) {
      navigator.geolocation.clearWatch(this.watchId)
    }
  }
}