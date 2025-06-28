import React, { createContext, useContext, useEffect, useState } from 'react';
import { STTService } from '@/services/stt/STTService';
import type { STTState, STTConfig } from '@/services/stt/types';

interface STTContextType {
  sttService: STTService;
  sttState: STTState;
  sttConfig: STTConfig;
  updateSTTConfig: (config: Partial<STTConfig>) => void;
}

const STTContext = createContext<STTContextType | null>(null);

export function STTProvider({ children }: { children: React.ReactNode }) {
  const [sttService] = useState(() => new STTService());
  const [sttState, setSTTState] = useState<STTState>({ status: 'idle' });
  const [sttConfig, setSTTConfig] = useState<STTConfig>(sttService.getConfig());

  useEffect(() => {
    const unsubscribe = sttService.onStateChange(setSTTState);
    return unsubscribe;
  }, [sttService]);

  const updateSTTConfig = (config: Partial<STTConfig>) => {
    sttService.updateConfig(config);
    setSTTConfig(sttService.getConfig());
  };

  return (
    <STTContext.Provider value={{
      sttService,
      sttState,
      sttConfig,
      updateSTTConfig
    }}>
      {children}
    </STTContext.Provider>
  );
}

export function useSTT() {
  const context = useContext(STTContext);
  if (!context) {
    throw new Error('useSTT must be used within a STTProvider');
  }
  return context;
}