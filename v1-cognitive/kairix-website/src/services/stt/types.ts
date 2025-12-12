export interface STTProvider {
  name: string;
  startRecording(): Promise<void>;
  stopRecording(): Promise<string>;
  abort(): void;
  isSupported(): boolean;
  onInterimResult?: (transcript: string) => void;
}

export interface STTConfig {
  provider: string;
  language?: string;
  continuous?: boolean;
  interimResults?: boolean;
  autoSubmit?: boolean; // Auto-submit transcription to chat
}

export type STTState = 
  | { status: 'idle' }
  | { status: 'listening'; interimTranscript?: string }
  | { status: 'processing' }
  | { status: 'transcribed'; transcript: string }
  | { status: 'error'; error: string };