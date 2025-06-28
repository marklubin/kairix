import React, { createContext, useContext, useEffect, useState } from 'react';
import { TTSService } from '@/services/tts/TTSService';
import type { TTSState, TTSConfig } from '@/services/tts/types';

interface TTSContextType {
  ttsService: TTSService;
  ttsState: TTSState;
  ttsConfig: TTSConfig;
  updateTTSConfig: (config: Partial<TTSConfig>) => void;
  isEnabled: boolean;
  setIsEnabled: (enabled: boolean) => void;
}

const TTSContext = createContext<TTSContextType | null>(null);

export function TTSProvider({ children }: { children: React.ReactNode }) {
  const [ttsService] = useState(() => new TTSService());
  const [ttsState, setTTSState] = useState<TTSState>({ status: 'waiting' });
  const [ttsConfig, setTTSConfig] = useState<TTSConfig>(ttsService.getConfig());
  const [isEnabled, setIsEnabled] = useState(true);

  useEffect(() => {
    // Subscribe to state changes
    const unsubscribe = ttsService.onStateChange(setTTSState);
    return unsubscribe;
  }, [ttsService]);

  const updateTTSConfig = (config: Partial<TTSConfig>) => {
    ttsService.updateConfig(config);
    setTTSConfig(ttsService.getConfig());
  };

  return (
    <TTSContext.Provider value={{
      ttsService,
      ttsState,
      ttsConfig,
      updateTTSConfig,
      isEnabled,
      setIsEnabled
    }}>
      {children}
    </TTSContext.Provider>
  );
}

export function useTTS() {
  const context = useContext(TTSContext);
  if (!context) {
    throw new Error('useTTS must be used within a TTSProvider');
  }
  return context;
}