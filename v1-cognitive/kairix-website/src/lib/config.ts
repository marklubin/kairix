// Single configuration object for all client app settings
const CONFIG_KEY = 'kairix_client_app_config';

// Get the Kairix server endpoint from environment variable
export const KAIRIX_SERVER_URL = import.meta.env.VITE_API_URL;
if (!KAIRIX_SERVER_URL) {
  throw new Error("VITE_API_URL env var not provided.");
}

const WEBSITE_PORT = import.meta.env.VITE_KAIRIX_WEBSITE_PORT

if(!WEBSITE_PORT){
  throw new Error("Port Env var not provided.")
}
console.log('Kairix client configuration:', {
  serverUrl: KAIRIX_SERVER_URL,
  websitePort: WEBSITE_PORT
});

export const defaultConfig = {
  // TTS Settings
  ttsProvider: 'elevenlabs',
  ttsEnabled: true,
  ttsVoice: '0NkECxcbkydDMspBKvQp',
  ttsRate: 1.2,
  ttsPitch: 1.0,
  ttsVolume: 1.0,
  ttsBufferWordCount: 20,
  
  // STT Settings
  sttProvider: 'browser',
  sttEnabled: true,
  whisperApiKey: '',
  
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