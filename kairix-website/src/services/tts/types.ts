export interface TTSProvider {
  name: string;
  speak(text: string, options?: TTSOptions): Promise<void>;
  stop(): void;
  getVoices(): Promise<TTSVoice[]>;
  isSupported(): boolean;
}

export interface TTSOptions {
  voice?: string;
  rate?: number;
  pitch?: number;
  volume?: number;
}

export interface TTSVoice {
  id: string;
  name: string;
  lang: string;
  localService?: boolean;
  quality?: 'standard' | 'premium' | 'neural' | 'personal';
  category?: 'system' | 'siri' | 'cloned';
  original?: SpeechSynthesisVoice;
}

export type TTSState = 
  | { status: 'idle' }
  | { status: 'waiting' }
  | { status: 'buffering'; text: string }
  | { status: 'rendering'; text: string }
  | { status: 'playing'; text: string }
  | { status: 'error'; error: string };

export interface TTSConfig {
  provider: string;
  voice?: string;
  rate?: number;
  pitch?: number;
  volume?: number;
  bufferWordCount?: number;
}