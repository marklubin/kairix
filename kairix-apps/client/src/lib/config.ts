// Single configuration object for all client app settings
const CONFIG_KEY = 'kairix_client_app_config';

// Detect if running on macOS
const isMacOS = typeof window !== 'undefined' && navigator.platform.toLowerCase().includes('mac');

export const defaultConfig = {
  // API Settings
  endpoint: 'http://localhost:8000',
  apiKey: '',
  
  // TTS Settings
  ttsProvider: isMacOS ? 'macos' : 'elevenlabs',
  ttsEnabled: true,
  elevenLabsApiKey: 'sk_f84893b970e13c43c23063f92abbcbc760698537780b5bfd',
  ttsVoice: isMacOS ? '' : '0NkECxcbkydDMspBKvQp',
  ttsRate: 1.0,
  ttsPitch: 1.0,
  ttsVolume: 1.0,
  ttsBufferWordCount: 10,
  
  // STT Settings
  sttProvider: 'browser',
  sttEnabled: true,
  whisperApiKey: '',
  
  // Model Settings
  selectedModel: 'gpt-4',
  
  // Other settings can be added here
};

export type AppConfig = typeof defaultConfig;

export function loadConfig(): AppConfig {
  try {
    const stored = localStorage.getItem(CONFIG_KEY);
    if (stored) {
      return { ...defaultConfig, ...JSON.parse(stored) };
    }
  } catch (e) {
    console.error('Failed to load config:', e);
  }
  return defaultConfig;
}

export function saveConfig(config: Partial<AppConfig>): void {
  try {
    const current = loadConfig();
    const updated = { ...current, ...config };
    localStorage.setItem(CONFIG_KEY, JSON.stringify(updated));
  } catch (e) {
    console.error('Failed to save config:', e);
  }
}

export function getConfigValue<K extends keyof AppConfig>(key: K): AppConfig[K] {
  const config = loadConfig();
  return config[key];
}

export function setConfigValue<K extends keyof AppConfig>(key: K, value: AppConfig[K]): void {
  saveConfig({ [key]: value });
}