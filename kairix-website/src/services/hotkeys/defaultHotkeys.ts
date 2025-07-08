import type { HotkeyAction } from './types';

export const DEFAULT_HOTKEYS: HotkeyAction[] = [
  // Navigation
  {
    id: 'focusInput',
    name: 'Focus Message Input',
    description: 'Focus the message input field',
    defaultKeys: 'cmd+l, ctrl+l',
    category: 'navigation'
  },
  {
    id: 'focusMessages',
    name: 'Focus Messages',
    description: 'Focus the messages area',
    defaultKeys: 'cmd+m, ctrl+m',
    category: 'navigation'
  },
  {
    id: 'scrollToBottom',
    name: 'Scroll to Bottom',
    description: 'Scroll to the latest message',
    defaultKeys: 'cmd+down, ctrl+down',
    category: 'navigation'
  },
  {
    id: 'scrollToTop',
    name: 'Scroll to Top',
    description: 'Scroll to the first message',
    defaultKeys: 'cmd+up, ctrl+up',
    category: 'navigation'
  },
  
  // Chat
  {
    id: 'sendMessage',
    name: 'Send Message',
    description: 'Send the current message',
    defaultKeys: 'cmd+enter, ctrl+enter',
    category: 'chat'
  },
  {
    id: 'stopGeneration',
    name: 'Stop Generation',
    description: 'Stop generating response',
    defaultKeys: 'escape',
    category: 'chat'
  },
  {
    id: 'clearInput',
    name: 'Clear Input',
    description: 'Clear the message input',
    defaultKeys: 'cmd+k, ctrl+k',
    category: 'chat'
  },
  {
    id: 'toggleSTT',
    name: 'Toggle Speech-to-Text',
    description: 'Start/stop voice recording',
    defaultKeys: 'cmd+shift+s, ctrl+shift+s',
    category: 'chat'
  },
  {
    id: 'newChat',
    name: 'New Chat',
    description: 'Clear chat history and start new',
    defaultKeys: 'cmd+shift+n, ctrl+shift+n',
    category: 'chat'
  },
  
  // Settings
  {
    id: 'toggleSidebar',
    name: 'Toggle Sidebar',
    description: 'Show/hide the settings sidebar',
    defaultKeys: 'cmd+/, ctrl+/',
    category: 'settings'
  },
  {
    id: 'toggleTTS',
    name: 'Toggle TTS',
    description: 'Enable/disable text-to-speech',
    defaultKeys: 'cmd+t, ctrl+t',
    category: 'settings'
  },
  {
    id: 'nextModel',
    name: 'Next Model',
    description: 'Switch to next model',
    defaultKeys: 'cmd+], ctrl+]',
    category: 'settings'
  },
  {
    id: 'previousModel',
    name: 'Previous Model',
    description: 'Switch to previous model',
    defaultKeys: 'cmd+[, ctrl+[',
    category: 'settings'
  },
  
  // General
  {
    id: 'showHotkeys',
    name: 'Show Hotkeys',
    description: 'Show/hide hotkey overlay',
    defaultKeys: 'cmd+?, ctrl+?',
    category: 'general'
  },
  {
    id: 'focusSearch',
    name: 'Search Messages',
    description: 'Search through messages',
    defaultKeys: 'cmd+f, ctrl+f',
    category: 'general'
  }
];

export function getDefaultHotkeyConfig(): Record<string, string> {
  return DEFAULT_HOTKEYS.reduce((acc, action) => {
    acc[action.id] = action.defaultKeys;
    return acc;
  }, {} as Record<string, string>);
}

export function getHotkeysByCategory() {
  const categories = {
    navigation: { name: 'Navigation', actions: [] as HotkeyAction[] },
    chat: { name: 'Chat', actions: [] as HotkeyAction[] },
    settings: { name: 'Settings', actions: [] as HotkeyAction[] },
    general: { name: 'General', actions: [] as HotkeyAction[] }
  };
  
  DEFAULT_HOTKEYS.forEach(action => {
    categories[action.category].actions.push(action);
  });
  
  return Object.values(categories);
}