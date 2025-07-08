// Phone Sensor Types for Real-time Streaming

export interface AccelerometerData {
  x: number; // m/s² - acceleration along x-axis
  y: number; // m/s² - acceleration along y-axis  
  z: number; // m/s² - acceleration along z-axis
  timestamp: number;
  // Derived values
  magnitude?: number; // sqrt(x² + y² + z²)
  includesGravity: boolean;
}

export interface GyroscopeData {
  alpha: number; // deg/s - rotation around z-axis
  beta: number;  // deg/s - rotation around x-axis
  gamma: number; // deg/s - rotation around y-axis
  timestamp: number;
}

export interface MagnetometerData {
  x: number; // μT - magnetic field x-component
  y: number; // μT - magnetic field y-component
  z: number; // μT - magnetic field z-component
  timestamp: number;
  // Derived values
  heading?: number; // degrees from magnetic north
  declination?: number; // magnetic declination
}

export interface OrientationData {
  alpha: number; // 0-360 degrees - rotation around z-axis (compass heading)
  beta: number;  // -180 to 180 degrees - rotation around x-axis (pitch)
  gamma: number; // -90 to 90 degrees - rotation around y-axis (roll)
  absolute: boolean; // true if relative to Earth's coordinate frame
  timestamp: number;
}

export interface LinearAccelerationData {
  x: number; // m/s² - acceleration without gravity
  y: number; // m/s²
  z: number; // m/s²
  timestamp: number;
}

export interface GravityData {
  x: number; // m/s² - gravity component
  y: number; // m/s²
  z: number; // m/s²
  timestamp: number;
}

export interface ProximityData {
  distance: number; // cm - distance to nearest object
  max: number; // maximum sensing distance
  near: boolean; // true if object is near
  timestamp: number;
}

export interface AmbientLightData {
  illuminance: number; // lux - light level
  timestamp: number;
  // Derived context
  lightCondition?: 'dark' | 'dim' | 'normal' | 'bright' | 'very-bright';
}

export interface PressureData {
  pressure: number; // hPa - atmospheric pressure
  altitude?: number; // meters - estimated altitude
  timestamp: number;
}

export interface RelativeHumidityData {
  humidity: number; // percentage 0-100
  timestamp: number;
}

export interface TemperatureData {
  ambient: number; // °C - ambient temperature
  device?: number; // °C - device temperature
  timestamp: number;
}

// High-frequency motion data
export interface MotionData {
  acceleration: AccelerometerData;
  accelerationIncludingGravity: AccelerometerData;
  rotationRate: GyroscopeData;
  orientation: OrientationData;
  interval: number; // ms - sampling interval
  timestamp: number;
}

// Derived motion patterns
export interface MotionPattern {
  type: 'stationary' | 'walking' | 'running' | 'driving' | 'cycling' | 'shaking' | 'falling';
  confidence: number; // 0-1
  details?: {
    steps?: number; // for walking/running
    speed?: number; // km/h
    cadence?: number; // steps/min or rpm
    gait?: 'normal' | 'irregular';
  };
  timestamp: number;
}

// Gesture detection
export interface GestureData {
  type: 'tap' | 'double-tap' | 'shake' | 'flip' | 'rotate' | 'tilt-left' | 'tilt-right' | 'face-up' | 'face-down';
  confidence: number;
  timestamp: number;
  rawData?: MotionData; // underlying sensor data
}

// WebSocket message types
export interface SensorStreamMessage {
  type: 'sensor_data' | 'pattern_detected' | 'gesture_detected' | 'config_update' | 'error';
  sessionId: string;
  deviceId: string;
  timestamp: number;
  data: SensorPayload;
}

export type SensorPayload = 
  | { type: 'motion'; data: MotionData }
  | { type: 'accelerometer'; data: AccelerometerData }
  | { type: 'gyroscope'; data: GyroscopeData }
  | { type: 'magnetometer'; data: MagnetometerData }
  | { type: 'orientation'; data: OrientationData }
  | { type: 'proximity'; data: ProximityData }
  | { type: 'ambient_light'; data: AmbientLightData }
  | { type: 'pressure'; data: PressureData }
  | { type: 'humidity'; data: RelativeHumidityData }
  | { type: 'temperature'; data: TemperatureData }
  | { type: 'pattern'; data: MotionPattern }
  | { type: 'gesture'; data: GestureData }
  | { type: 'batch'; data: SensorPayload[] }; // for buffered updates

// Streaming configuration
export interface SensorStreamConfig {
  // Which sensors to enable
  sensors: {
    motion: boolean;
    accelerometer: boolean;
    gyroscope: boolean;
    magnetometer: boolean;
    orientation: boolean;
    proximity: boolean;
    ambientLight: boolean;
    pressure: boolean;
    humidity: boolean;
    temperature: boolean;
  };
  
  // Sampling rates (Hz)
  sampleRates: {
    motion: number; // typically 60Hz for smooth motion
    environmental: number; // typically 1Hz for ambient sensors
  };
  
  // Processing options
  processing: {
    detectPatterns: boolean; // walking, running, etc.
    detectGestures: boolean; // shakes, taps, etc.
    smoothing: boolean; // apply low-pass filter
    calibrate: boolean; // auto-calibrate sensors
  };
  
  // Transmission options
  transmission: {
    mode: 'realtime' | 'batch' | 'adaptive';
    batchSize?: number; // for batch mode
    batchInterval?: number; // ms
    compression: boolean;
    throttleRate?: number; // max messages per second
  };
  
  // Power management
  powerMode: 'high-performance' | 'balanced' | 'power-saver';
}

// Server-side aggregated data
export interface SensorAnalytics {
  sessionId: string;
  duration: number; // ms
  
  motion: {
    totalDistance?: number; // meters
    averageSpeed?: number; // km/h
    maxAcceleration?: number; // m/s²
    activityBreakdown: Record<string, number>; // time spent in each activity
    stepCount?: number;
  };
  
  environment: {
    lightExposure?: number; // average lux
    temperatureRange?: { min: number; max: number };
    altitudeChange?: number; // meters
  };
  
  patterns: {
    detectedGestures: GestureData[];
    significantMotions: MotionPattern[];
    anomalies?: Array<{
      type: string;
      timestamp: number;
      severity: 'low' | 'medium' | 'high';
    }>;
  };
}

// WebSocket connection state
export interface SensorStreamState {
  connected: boolean;
  streaming: boolean;
  lastUpdate: number;
  errorCount: number;
  bufferedMessages: number;
  sensors: Record<string, {
    available: boolean;
    active: boolean;
    lastReading: number;
    errorRate: number;
  }>;
}