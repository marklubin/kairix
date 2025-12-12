export interface HotkeyAction {
  id: string;
  name: string;
  description: string;
  defaultKeys: string;
  category: 'navigation' | 'chat' | 'settings' | 'general';
}

export interface HotkeyConfig {
  [actionId: string]: string; // actionId -> hotkey string
}

export interface HotkeyCategory {
  name: string;
  actions: HotkeyAction[];
}