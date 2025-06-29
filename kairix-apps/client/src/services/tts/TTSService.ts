import type { TTSProvider, TTSState, TTSConfig } from './types';
import { BrowserTTSProvider } from './providers/BrowserTTSProvider';
import { ElevenLabsTTSProvider } from './providers/ElevenLabsTTSProvider';

export class TTSService {
  private provider: TTSProvider;
  private config: TTSConfig;
  private buffer: string = '';
  private isProcessing: boolean = false;
  private queue: string[] = [];
  private stateListeners: ((state: TTSState) => void)[] = [];
  private currentState: TTSState = { status: 'waiting' };
  private abortController: AbortController | null = null;
  private interruptedMessageIds = new Set<string>();
  private currentMessageId: string | null = null;

  constructor(config?: Partial<TTSConfig>) {
    this.config = {
      provider: 'elevenlabs',
      voice: '0NkECxcbkydDMspBKvQp', // Apiana voice
      rate: 1.0,
      pitch: 1.0,
      volume: 1.0,
      elevenLabsApiKey: 'sk_f84893b970e13c43c23063f92abbcbc760698537780b5bfd',
      ...config
    };

    // Initialize provider based on config
    this.provider = this.createProvider(this.config.provider);
  }

  private createProvider(providerName: string): TTSProvider {
    switch (providerName) {
      case 'browser':
        return new BrowserTTSProvider();
      case 'elevenlabs':
        return new ElevenLabsTTSProvider(this.config.elevenLabsApiKey);
      default:
        throw new Error(`Unknown TTS provider: ${providerName}`);
    }
  }

  setProvider(providerName: string): void {
    this.stop();
    this.provider = this.createProvider(providerName);
    this.config.provider = providerName;
  }

  onStateChange(listener: (state: TTSState) => void): () => void {
    this.stateListeners.push(listener);
    // Return unsubscribe function
    return () => {
      this.stateListeners = this.stateListeners.filter(l => l !== listener);
    };
  }

  private setState(state: TTSState): void {
    this.currentState = state;
    this.stateListeners.forEach(listener => listener(state));
  }

  getState(): TTSState {
    return this.currentState;
  }

  // Check if buffer ends with a phrase completion character
  private isCompletedPhrase(buffer: string): boolean {
    if (!buffer) return false;
    const lastChar = buffer[buffer.length - 1];
    return lastChar === ',' || lastChar === '.' || lastChar === '-';
  }

  // Process streaming text input
  processStreamingText(text: string, messageId?: string): void {
    if (!text) return;

    // Don't process text for interrupted messages
    if (messageId && this.interruptedMessageIds.has(messageId)) {
      return;
    }

    // Track current message
    if (messageId) {
      this.currentMessageId = messageId;
    }

    // Add to buffer
    this.buffer += text;
    this.setState({ status: 'buffering', text: this.buffer });

    // Check if we have a completed phrase
    if (this.isCompletedPhrase(this.buffer)) {
      // Process the buffer immediately
      this.queue.push(this.buffer);
      this.buffer = ''; // Clear buffer after queuing
      this.processQueue();
    }
    // No timeout - just wait for stop chars or explicit finish
  }


  private flushBuffer(): void {
    if (this.buffer.trim()) {
      this.queue.push(this.buffer.trim());
      this.buffer = '';
      this.processQueue();
    }
  }

  private async processQueue(): Promise<void> {
    if (this.isProcessing || this.queue.length === 0) {
      return;
    }

    this.isProcessing = true;

    while (this.queue.length > 0) {
      const text = this.queue.shift()!;
      
      try {
        // Update state to rendering
        this.setState({ status: 'rendering', text });

        // Create abort controller for this segment
        this.abortController = new AbortController();

        // Speak the text
        this.setState({ status: 'playing', text });
        await this.provider.speak(text, {
          voice: this.config.voice,
          rate: this.config.rate,
          pitch: this.config.pitch,
          volume: this.config.volume,
        });

      } catch (error) {
        console.error('TTS Error:', error);
        this.setState({ status: 'error', error: error instanceof Error ? error.message : 'Unknown error' });
        
        // Continue processing remaining queue items after error
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1s before retrying
      }
    }

    this.isProcessing = false;
    this.abortController = null;

    // Reset to waiting if no more items and no buffer
    if (this.queue.length === 0 && !this.buffer.trim()) {
      this.setState({ status: 'waiting' });
    } else if (this.buffer.trim()) {
      this.setState({ status: 'buffering', text: this.buffer });
    }
  }

  // Call this when streaming is complete
  finishStreaming(): void {
    // Process any remaining buffer when streaming ends
    this.flushBuffer();
  }

  stop(): void {
    // Clear buffer and queue
    this.buffer = '';
    this.queue = [];
    this.isProcessing = false;

    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }

    // Stop provider
    this.provider.stop();
    
    // Reset state
    this.setState({ status: 'waiting' });
  }

  async getVoices() {
    return this.provider.getVoices();
  }

  updateConfig(config: Partial<TTSConfig>): void {
    this.config = { ...this.config, ...config };
    
    // If provider changed or ElevenLabs API key updated, recreate provider
    if (config.provider && config.provider !== this.provider.name) {
      this.setProvider(config.provider);
    } else if (config.elevenLabsApiKey !== undefined && this.config.provider === 'elevenlabs') {
      // Recreate ElevenLabs provider with new API key
      this.provider = new ElevenLabsTTSProvider(config.elevenLabsApiKey);
    }
  }

  getConfig(): TTSConfig {
    return { ...this.config };
  }

  // Interrupt TTS for a specific message
  interruptMessage(messageId?: string): void {
    if (messageId) {
      this.interruptedMessageIds.add(messageId);
    } else if (this.currentMessageId) {
      this.interruptedMessageIds.add(this.currentMessageId);
    }
    
    // Stop current playback
    this.stop();
  }

  // Check if new message to clear interruption
  startNewMessage(messageId: string): void {
    this.currentMessageId = messageId;
    // Messages are no longer interrupted once a new message starts
  }
}