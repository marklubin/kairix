import type { STTProvider, STTState, STTConfig } from './types';
import { BrowserSTTProvider } from './providers/BrowserSTTProvider';
import { WhisperSTTProvider } from './providers/WhisperSTTProvider';
import { WhisperMobileSTTProvider } from './providers/WhisperMobileSTTProvider';
import { WhisperUnifiedSTTProvider } from './providers/WhisperUnifiedSTTProvider';

export class STTService {
  private provider: STTProvider;
  private config: STTConfig;
  private stateListeners: ((state: STTState) => void)[] = [];
  private currentState: STTState = { status: 'idle' };
  private isRecording = false;
  private currentMessageId: string | null = null; // Track which message triggered TTS interruption

  constructor(config?: Partial<STTConfig>) {
    // Use browser STT for immediate response
    const defaultProvider = 'browser';
    
    this.config = {
      provider: defaultProvider,
      language: 'en-US',
      continuous: true,  // Enable continuous mode for streaming
      interimResults: true,
      autoSubmit: false,  // NEVER auto-submit
      ...config
    };

    console.log('STTService: Using unified Whisper provider:', this.config.provider);
    this.provider = this.createProvider(this.config.provider);
  }

  private createProvider(providerName: string): STTProvider {
    switch (providerName) {
      case 'browser': {
        const provider = new BrowserSTTProvider(
          this.config.language,
          this.config.continuous,
          this.config.interimResults
        );
        // Set up interim result handler
        provider.onInterimResult = (transcript) => {
          this.setState({ status: 'listening', interimTranscript: transcript });
        };
        return provider;
      }
      case 'whisper': {
        const provider = new WhisperSTTProvider();
        return provider;
      }
      case 'whisper-mobile': {
        const provider = new WhisperMobileSTTProvider();
        // Set up interim result handler
        provider.onInterimResult = (transcript) => {
          this.setState({ status: 'listening', interimTranscript: transcript });
        };
        return provider;
      }
      case 'whisper-unified': {
        const provider = new WhisperUnifiedSTTProvider();
        // Set up interim result handler
        provider.onInterimResult = (transcript) => {
          this.setState({ status: 'listening', interimTranscript: transcript });
        };
        return provider;
      }
      default:
        throw new Error(`Unknown STT provider: ${providerName}`);
    }
  }

  setProvider(providerName: string): void {
    this.abort();
    this.provider = this.createProvider(providerName);
    this.config.provider = providerName;
  }

  onStateChange(listener: (state: STTState) => void): () => void {
    this.stateListeners.push(listener);
    return () => {
      this.stateListeners = this.stateListeners.filter(l => l !== listener);
    };
  }

  private setState(state: STTState): void {
    console.log('STTService setState:', state);
    this.currentState = state;
    this.stateListeners.forEach(listener => listener(state));
  }

  getState(): STTState {
    return this.currentState;
  }
  
  resetState(): void {
    this.setState({ status: 'idle' });
  }

  async toggleRecording(): Promise<string | null> {
    if (this.isRecording) {
      return this.stopRecording();
    } else {
      await this.startRecording();
      return null;
    }
  }

  async startRecording(messageId?: string): Promise<void> {
    if (this.isRecording) {
      console.warn('Already recording');
      return;
    }

    try {
      this.isRecording = true;
      this.currentMessageId = messageId || null;
      this.setState({ status: 'listening' });
      await this.provider.startRecording();
    } catch (error) {
      this.isRecording = false;
      this.currentMessageId = null;
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.setState({ status: 'error', error: errorMessage });
      throw error;
    }
  }

  async stopRecording(): Promise<string> {
    // More lenient check - if we're in listening state, we can stop
    if (!this.isRecording && this.currentState.status !== 'listening') {
      console.warn('Attempted to stop recording but not in recording state');
      return '';
    }

    try {
      this.setState({ status: 'processing' });
      
      // Only try to stop the provider if it's actually recording
      let transcript = '';
      if (this.isRecording) {
        transcript = await this.provider.stopRecording();
      }
      
      console.log('STTService received transcript:', transcript);
      this.isRecording = false;
      
      if (transcript) {
        console.log('Setting state to transcribed with:', transcript);
        this.setState({ status: 'transcribed', transcript });
      } else {
        console.log('No transcript, setting state to idle');
        this.setState({ status: 'idle' });
      }
      
      this.currentMessageId = null;
      
      return transcript;
    } catch (error) {
      this.isRecording = false;
      this.currentMessageId = null;
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      this.setState({ status: 'error', error: errorMessage });
      throw error;
    }
  }

  abort(): void {
    if (this.isRecording) {
      this.provider.abort();
      this.isRecording = false;
      this.currentMessageId = null;
      this.setState({ status: 'idle' });
    }
  }

  getCurrentMessageId(): string | null {
    return this.currentMessageId;
  }

  updateConfig(config: Partial<STTConfig>): void {
    this.config = { ...this.config, ...config };
    
    if (config.provider && config.provider !== this.provider.name) {
      this.setProvider(config.provider);
    } else if (config.language || config.continuous !== undefined || config.interimResults !== undefined) {
      // Recreate provider with new settings
      this.provider = this.createProvider(this.config.provider);
    }
  }

  getConfig(): STTConfig {
    return { ...this.config };
  }

  isAutoSubmitEnabled(): boolean {
    // NEVER auto-submit - user must manually click button
    return false;
  }
  
  clearTranscript(): void {
    // Clear the accumulated transcript in the provider
    if (this.provider && 'clearTranscript' in this.provider) {
      (this.provider as any).clearTranscript();
    }
    this.setState({ status: 'idle' });
  }
}