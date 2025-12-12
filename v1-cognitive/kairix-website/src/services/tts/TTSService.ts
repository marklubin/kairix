import type { TTSProvider, TTSState, TTSConfig } from './types';
import { BrowserTTSProvider } from './providers/BrowserTTSProvider';
import { ElevenLabsTTSProvider } from './providers/ElevenLabsTTSProvider';
import { MacOSTTSProvider } from './providers/MacOSTTSProvider';
import { loadConfig, saveConfig } from '@/lib/config';

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
    // Load from centralized config
    const appConfig = loadConfig();
    
    this.config = {
      provider: appConfig.ttsProvider,
      voice: appConfig.ttsVoice,
      rate: appConfig.ttsRate,
      pitch: appConfig.ttsPitch,
      volume: appConfig.ttsVolume,
      bufferWordCount: appConfig.ttsBufferWordCount,
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
        return new ElevenLabsTTSProvider();
      case 'macos':
        return new MacOSTTSProvider();
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

  // Count words in the buffer
  private countWords(text: string): number {
    return text.trim().split(/\s+/).filter(word => word.length > 0).length;
  }

  // Check if buffer has a pause condition (punctuation)
  private hasPauseCondition(buffer: string): boolean {
    // Check for common pause punctuation
    return /[.!?;,\-—:]\s*$/.test(buffer);
  }

  // Check if buffer contains a paragraph break
  private hasParagraphBreak(text: string): boolean {
    // Check for double newlines, or newline followed by whitespace and another newline
    return /\n\s*\n/.test(text);
  }

  // Check if buffer is ready to be processed
  private shouldProcessBuffer(buffer: string): boolean {
    const wordCount = this.countWords(buffer);
    const hasPause = this.hasPauseCondition(buffer);
    
    // Process if:
    // 1. We have at least bufferWordCount words AND a pause condition, OR
    // 2. We have a completed phrase (legacy check for backward compatibility), OR
    // 3. We have a paragraph break (always process on paragraph breaks)
    const minWordCount = this.config.bufferWordCount || 10;
    return (wordCount >= minWordCount && hasPause) || this.isCompletedPhrase(buffer) || this.hasParagraphBreak(buffer);
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

    // Check if buffer is ready to be processed
    if (this.shouldProcessBuffer(this.buffer)) {
      // Process the buffer
      this.queue.push(this.buffer);
      this.buffer = ''; // Clear buffer after queuing
      this.processQueue();
    }
    // Wait for buffering conditions or explicit finish
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
    
    // Save to centralized config
    saveConfig({
      ttsProvider: this.config.provider,
      ttsVoice: this.config.voice,
      ttsRate: this.config.rate,
      ttsPitch: this.config.pitch,
      ttsVolume: this.config.volume,
      ttsBufferWordCount: this.config.bufferWordCount
    });
    
    // If provider changed, recreate provider
    if (config.provider && config.provider !== this.provider.name) {
      this.setProvider(config.provider);
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