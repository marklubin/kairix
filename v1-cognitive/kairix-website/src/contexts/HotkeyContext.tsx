import React, { createContext, useContext, useState, useEffect } from 'react';
import { useHotkeys } from 'react-hotkeys-hook';
import { getDefaultHotkeyConfig, DEFAULT_HOTKEYS } from '@/services/hotkeys/defaultHotkeys';
import type { HotkeyConfig } from '@/services/hotkeys/types';
import { flashHotkey } from '@/components/ui/hotkey-flash';

interface HotkeyContextType {
  hotkeyConfig: HotkeyConfig;
  updateHotkey: (actionId: string, keys: string) => void;
  resetHotkeys: () => void;
  showOverlay: boolean;
  setShowOverlay: (show: boolean) => void;
  registerAction: (actionId: string, callback: () => void, deps?: any[]) => void;
}

const HotkeyContext = createContext<HotkeyContextType | null>(null);

const STORAGE_KEY = 'chat-hotkeys';

export function HotkeyProvider({ children }: { children: React.ReactNode }) {
  const [hotkeyConfig, setHotkeyConfig] = useState<HotkeyConfig>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : getDefaultHotkeyConfig();
  });
  
  const [showOverlay, setShowOverlay] = useState(false);
  const [registeredActions] = useState(new Map<string, () => void>());

  // Save config to localStorage when it changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(hotkeyConfig));
  }, [hotkeyConfig]);

  const updateHotkey = (actionId: string, keys: string) => {
    setHotkeyConfig(prev => ({
      ...prev,
      [actionId]: keys
    }));
  };

  const resetHotkeys = () => {
    const defaults = getDefaultHotkeyConfig();
    setHotkeyConfig(defaults);
  };

  const registerAction = (actionId: string, callback: () => void, deps: any[] = []) => {
    registeredActions.set(actionId, callback);
    
    // Use the hotkey hook directly here
    const keys = hotkeyConfig[actionId];
    if (keys) {
      // Find the action details
      const action = DEFAULT_HOTKEYS.find(a => a.id === actionId);
      
      // Wrap callback to show flash
      const wrappedCallback = () => {
        if (action) {
          flashHotkey(keys, action.name);
        }
        callback();
      };
      
      // eslint-disable-next-line react-hooks/rules-of-hooks
      useHotkeys(keys, wrappedCallback, { enableOnFormTags: ['INPUT', 'TEXTAREA'] }, [hotkeyConfig[actionId], ...deps]);
    }
  };

  // Register global hotkey for showing overlay
  useHotkeys(hotkeyConfig.showHotkeys || 'cmd+?, ctrl+?', () => {
    flashHotkey(hotkeyConfig.showHotkeys || 'cmd+?, ctrl+?', 'Show Hotkeys');
    setShowOverlay(prev => !prev);
  }, { enableOnFormTags: true }, [hotkeyConfig.showHotkeys]);

  return (
    <HotkeyContext.Provider value={{
      hotkeyConfig,
      updateHotkey,
      resetHotkeys,
      showOverlay,
      setShowOverlay,
      registerAction
    }}>
      {children}
    </HotkeyContext.Provider>
  );
}

export function useHotkey() {
  const context = useContext(HotkeyContext);
  if (!context) {
    throw new Error('useHotkey must be used within a HotkeyProvider');
  }
  return context;
}