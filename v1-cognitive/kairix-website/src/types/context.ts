// Context API Types

export interface GeolocationContext {
  latitude: number;
  longitude: number;
  accuracy: number; // meters
  altitude?: number | null; // meters
  altitudeAccuracy?: number | null; // meters
  heading?: number | null; // degrees from north
  speed?: number | null; // meters/second
  timestamp: number;
  // Derived data
  address?: {
    street?: string;
    city?: string;
    state?: string;
    country?: string;
    postalCode?: string;
    formatted?: string;
  };
}

export interface DeviceContext {
  // Device info
  platform: string; // e.g., "MacIntel", "Win32", "Linux x86_64"
  userAgent: string;
  language: string; // e.g., "en-US"
  languages: string[]; // preferred languages
  screenResolution: {
    width: number;
    height: number;
    pixelRatio: number;
  };
  
  // Capabilities
  touchEnabled: boolean;
  onLine: boolean;
  connectionType?: string; // "wifi", "cellular", "ethernet", etc.
  effectiveConnectionType?: string; // "slow-2g", "2g", "3g", "4g"
  
  // Battery (if available)
  battery?: {
    level: number; // 0-1
    charging: boolean;
    chargingTime?: number; // seconds
    dischargingTime?: number; // seconds
  };
  
  // Memory (if available)
  memory?: {
    deviceMemory?: number; // GB
    usedJSHeapSize?: number; // bytes
    totalJSHeapSize?: number; // bytes
    jsHeapSizeLimit?: number; // bytes
  };
}

export interface EnvironmentContext {
  // Time and timezone
  timezone: string; // e.g., "America/New_York"
  timezoneOffset: number; // minutes from UTC
  localTime: string; // ISO string
  isDarkMode: boolean;
  
  // Weather (if integrated)
  weather?: {
    temperature?: number; // Celsius
    feelsLike?: number;
    humidity?: number; // percentage
    pressure?: number; // hPa
    windSpeed?: number; // m/s
    windDirection?: number; // degrees
    description?: string; // e.g., "partly cloudy"
    icon?: string;
  };
  
  // Ambient
  ambientLight?: number; // lux (if light sensor available)
  ambientNoise?: number; // dB (if permission granted)
}

export interface ActivityContext {
  // Page/App context
  currentUrl: string;
  pageTitle: string;
  referrer?: string;
  sessionDuration: number; // milliseconds
  
  // User activity
  lastActiveTimestamp: number;
  idleTime: number; // milliseconds
  
  // Motion (if available)
  motion?: {
    acceleration?: {
      x: number;
      y: number;
      z: number;
    };
    rotationRate?: {
      alpha: number;
      beta: number;
      gamma: number;
    };
    interval: number;
  };
  
  // Detected activity (if permission granted)
  activityType?: 'stationary' | 'walking' | 'running' | 'automotive' | 'cycling' | 'unknown';
  confidence?: number; // 0-1
}

export interface CalendarContext {
  // Current user's calendar state (if integrated)
  currentEvent?: {
    title: string;
    startTime: string;
    endTime: string;
    location?: string;
    type?: string; // "meeting", "focus", "break", etc.
  };
  
  nextEvent?: {
    title: string;
    startTime: string;
    minutesUntil: number;
  };
  
  // Availability
  isAvailable: boolean;
  nextAvailableSlot?: string;
}

export interface MediaContext {
  // Currently playing media
  playingMedia?: {
    title?: string;
    artist?: string;
    duration?: number;
    currentTime?: number;
    source: 'spotify' | 'apple_music' | 'youtube' | 'browser' | 'other';
    state: 'playing' | 'paused';
  };
  
  // Camera status (for privacy)
  cameraActive: boolean;
  microphoneActive: boolean;
  screenShareActive: boolean;
}

export interface ContextUpdate {
  // Unique ID for this update
  id: string;
  timestamp: number;
  
  // Context types included in this update
  contexts: {
    geolocation?: GeolocationContext;
    device?: DeviceContext;
    environment?: EnvironmentContext;
    activity?: ActivityContext;
    calendar?: CalendarContext;
    media?: MediaContext;
    custom?: Record<string, any>; // For extensibility
  };
  
  // Update metadata
  trigger: 'manual' | 'periodic' | 'significant_change' | 'request';
  priority: 'low' | 'normal' | 'high';
}

// API Request/Response types
export interface ContextUpdateRequest {
  updates: ContextUpdate[];
  clientId: string;
  sessionId: string;
}

export interface ContextUpdateResponse {
  accepted: boolean;
  processedIds: string[];
  errors?: Array<{
    id: string;
    error: string;
  }>;
}

// Permissions and Privacy
export interface ContextPermissions {
  geolocation: 'granted' | 'denied' | 'prompt';
  motion: 'granted' | 'denied' | 'prompt';
  camera: 'granted' | 'denied' | 'prompt';
  microphone: 'granted' | 'denied' | 'prompt';
  notifications: 'granted' | 'denied' | 'prompt';
  // Custom permissions
  calendar?: 'granted' | 'denied' | 'prompt';
  weather?: 'granted' | 'denied' | 'prompt';
  activity?: 'granted' | 'denied' | 'prompt';
}

// Configuration for context collection
export interface ContextConfig {
  // What to collect
  enabledContexts: {
    geolocation: boolean;
    device: boolean;
    environment: boolean;
    activity: boolean;
    calendar: boolean;
    media: boolean;
  };
  
  // Collection settings
  updateInterval: number; // milliseconds
  significantChangeThresholds: {
    location: number; // meters
    activity: number; // confidence change
    light: number; // lux change
  };
  
  // Privacy settings
  anonymizeData: boolean;
  retentionPeriod: number; // milliseconds
  shareWithThirdParties: boolean;
}