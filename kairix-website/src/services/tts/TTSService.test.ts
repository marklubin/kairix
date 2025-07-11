import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { TTSService } from './TTSService';
import type { TTSProvider } from './types';
import { loadConfig, saveConfig } from '@/lib/config';

// Mock the config module
vi.mock('@/lib/config');

// Mock the providers
vi.mock('./providers/BrowserTTSProvider', () => ({
  BrowserTTSProvider: vi.fn().mockImplementation(() => ({
    name: 'browser',
    speak: vi.fn().mockResolvedValue(undefined),
    stop: vi.fn(),
    getVoices: vi.fn().mockResolvedValue([
      { id: 'browser-voice-1', name: 'Google US English', lang: 'en-US' },
      { id: 'browser-voice-2', name: 'Google UK English', lang: 'en-GB' },
    ]),
    isSupported: vi.fn().mockReturnValue(true),
  })),
}));

vi.mock('./providers/ElevenLabsTTSProvider', () => ({
  ElevenLabsTTSProvider: vi.fn().mockImplementation(() => ({
    name: 'elevenlabs',
    speak: vi.fn().mockResolvedValue(undefined),
    stop: vi.fn(),
    getVoices: vi.fn().mockResolvedValue([
      { id: '0NkECxcbkydDMspBKvQp', name: 'Rachel', lang: 'en' },
      { id: 'elevenlabs-voice-2', name: 'Josh', lang: 'en' },
    ]),
    isSupported: vi.fn().mockReturnValue(true),
  })),
}));

vi.mock('./providers/MacOSTTSProvider', () => ({
  MacOSTTSProvider: vi.fn().mockImplementation(() => ({
    name: 'macos',
    speak: vi.fn().mockResolvedValue(undefined),
    stop: vi.fn(),
    getVoices: vi.fn().mockResolvedValue([
      { id: 'macos-voice-1', name: 'Samantha', lang: 'en-US' },
    ]),
    isSupported: vi.fn().mockReturnValue(true),
  })),
}));

describe('TTSService', () => {
  let ttsService: TTSService;
  let mockProvider: TTSProvider;

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock default config
    vi.mocked(loadConfig).mockReturnValue({
      ttsProvider: 'elevenlabs',
      ttsEnabled: true,
      elevenLabsApiKey: 'sk_c467a0c77dd236d4fac4a9cc7cbd5d2aad561771b7d3a18f',
      ttsVoice: '0NkECxcbkydDMspBKvQp',
      ttsRate: 1.0,
      ttsPitch: 1.0,
      ttsVolume: 1.0,
      ttsBufferWordCount: 10,
      sttProvider: 'browser',
      sttEnabled: true,
      whisperApiKey: '',
    });
    
    ttsService = new TTSService();
    // Get the mock provider
    mockProvider = (ttsService as any).provider;
  });

  afterEach(() => {
    if (ttsService) {
      ttsService.stop();
    }
    vi.clearAllMocks();
  });

  describe('buffering logic', () => {
    it('should not process buffer with fewer than 10 words without pause', () => {
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      ttsService.processStreamingText('Hello world this is');
      expect(spy).not.toHaveBeenCalled();
      
      ttsService.processStreamingText(' a test message');
      expect(spy).not.toHaveBeenCalled();
    });

    it('should process buffer with 10+ words and pause condition', () => {
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      // Add exactly 10 words with a comma at the end
      ttsService.processStreamingText('This is a test message with exactly ten words here,');
      expect(spy).toHaveBeenCalled();
    });

    it('should process buffer with 10+ words and period', () => {
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      ttsService.processStreamingText('This is a longer test message that contains more than ten words.');
      expect(spy).toHaveBeenCalled();
    });

    it('should process buffer with 10+ words and question mark', () => {
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      ttsService.processStreamingText('How can we test this feature with more than ten words effectively?');
      expect(spy).toHaveBeenCalled();
    });

    it('should not process buffer with 10+ words but no pause', () => {
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      ttsService.processStreamingText('This is a longer test message that contains more than ten words without punctuation');
      expect(spy).not.toHaveBeenCalled();
    });

    it('should respect custom buffer word count', () => {
      // Create service with custom buffer count
      const customService = new TTSService({ provider: 'browser', bufferWordCount: 5 });
      const spy = vi.spyOn(customService as any, 'processQueue');
      
      // Should process with just 5 words and pause
      customService.processStreamingText('This is only five words.');
      expect(spy).toHaveBeenCalled();
    });

    it('should update buffer word count dynamically', () => {
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      // Update config to require only 3 words
      ttsService.updateConfig({ bufferWordCount: 3 });
      
      // Should process with just 3 words and pause
      ttsService.processStreamingText('Three words here.');
      expect(spy).toHaveBeenCalled();
    });

    it('should process buffer on legacy completed phrase (backward compatibility)', () => {
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      // Less than 10 words but ends with comma (legacy behavior)
      ttsService.processStreamingText('Hello world,');
      expect(spy).toHaveBeenCalled();
    });

    it('should accumulate text across multiple calls', () => {
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      ttsService.processStreamingText('This is the');
      expect(spy).not.toHaveBeenCalled();
      
      ttsService.processStreamingText(' beginning of a');
      expect(spy).not.toHaveBeenCalled();
      
      ttsService.processStreamingText(' longer message that will');
      expect(spy).not.toHaveBeenCalled();
      
      ttsService.processStreamingText(' eventually have enough words.');
      expect(spy).toHaveBeenCalled();
    });

    it('should clear buffer after processing', () => {
      ttsService.processStreamingText('This is a test message with more than ten words in it.');
      
      // Add more text after processing
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      spy.mockClear();
      
      ttsService.processStreamingText('Short text');
      expect(spy).not.toHaveBeenCalled();
    });

    it('should handle various pause punctuation marks', () => {
      const testCases = [
        'with a semicolon at the end of this longer phrase;',
        'with a colon at the end of this longer phrase:',
        'with a dash at the end of this longer phrase-',
        'with an em dash at the end of this longer phrase—',
        'with an exclamation at the end of this longer phrase!',
      ];

      testCases.forEach(text => {
        const service = new TTSService({ provider: 'browser' });
        const spy = vi.spyOn(service as any, 'processQueue');
        
        // Add enough words with punctuation (total will be 10+ words)
        service.processStreamingText('This is a test message ' + text);
        expect(spy).toHaveBeenCalled();
      });
    });
  });

  describe('finishStreaming', () => {
    it('should flush buffer when streaming ends', () => {
      const flushSpy = vi.spyOn(ttsService as any, 'flushBuffer');
      
      ttsService.processStreamingText('This is some text without enough words');
      ttsService.finishStreaming();
      
      expect(flushSpy).toHaveBeenCalled();
    });

    it('should process remaining buffer content on finish', () => {
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      // Add text that doesn't meet buffering criteria
      ttsService.processStreamingText('Short text');
      expect(spy).not.toHaveBeenCalled();
      
      // Finish streaming should process it
      ttsService.finishStreaming();
      expect(spy).toHaveBeenCalled();
    });

    it('should not process empty buffer on finish', () => {
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      ttsService.finishStreaming();
      expect(spy).not.toHaveBeenCalled();
    });
  });

  describe('word counting', () => {
    it('should count words correctly', () => {
      const countWords = (ttsService as any).countWords.bind(ttsService);
      
      expect(countWords('Hello world')).toBe(2);
      expect(countWords('  Multiple   spaces   between   words  ')).toBe(4);
      expect(countWords('One')).toBe(1);
      expect(countWords('')).toBe(0);
      expect(countWords('   ')).toBe(0);
      expect(countWords('This is a test with five words.')).toBe(7);
    });
  });

  describe('pause detection', () => {
    it('should detect pause conditions correctly', () => {
      const hasPause = (ttsService as any).hasPauseCondition.bind(ttsService);
      
      // Should detect pauses
      expect(hasPause('Hello.')).toBe(true);
      expect(hasPause('Hello!')).toBe(true);
      expect(hasPause('Hello?')).toBe(true);
      expect(hasPause('Hello,')).toBe(true);
      expect(hasPause('Hello;')).toBe(true);
      expect(hasPause('Hello:')).toBe(true);
      expect(hasPause('Hello-')).toBe(true);
      expect(hasPause('Hello—')).toBe(true);
      expect(hasPause('Hello. ')).toBe(true);
      expect(hasPause('Hello.  ')).toBe(true);
      
      // Should not detect pauses
      expect(hasPause('Hello')).toBe(false);
      expect(hasPause('Hello world')).toBe(false);
      expect(hasPause('')).toBe(false);
    });
  });

  describe('paragraph break detection', () => {
    it('should detect paragraph breaks correctly', () => {
      const hasParagraph = (ttsService as any).hasParagraphBreak.bind(ttsService);
      
      // Should detect paragraph breaks
      expect(hasParagraph('First paragraph\n\nSecond paragraph')).toBe(true);
      expect(hasParagraph('First paragraph\n \nSecond paragraph')).toBe(true);
      expect(hasParagraph('First paragraph\n  \nSecond paragraph')).toBe(true);
      expect(hasParagraph('First paragraph\n\t\nSecond paragraph')).toBe(true);
      expect(hasParagraph('Text with\n\n\nmultiple breaks')).toBe(true);
      
      // Should not detect paragraph breaks
      expect(hasParagraph('Single line')).toBe(false);
      expect(hasParagraph('Line one\nLine two')).toBe(false);
      expect(hasParagraph('')).toBe(false);
      expect(hasParagraph('\n')).toBe(false);
      expect(hasParagraph('Text with spaces  ')).toBe(false);
    });

    it('should process buffer immediately on paragraph break', () => {
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      // Even with few words, paragraph break should trigger processing
      ttsService.processStreamingText('Short text\n\nNew paragraph');
      expect(spy).toHaveBeenCalled();
    });

    it('should process buffer with paragraph break in streaming', () => {
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      ttsService.processStreamingText('First part');
      expect(spy).not.toHaveBeenCalled();
      
      ttsService.processStreamingText('\n\nSecond part');
      expect(spy).toHaveBeenCalled();
    });
  });

  describe('state management', () => {
    it('should update state during buffering', () => {
      const stateListener = vi.fn();
      ttsService.onStateChange(stateListener);
      
      ttsService.processStreamingText('Hello world');
      
      expect(stateListener).toHaveBeenCalledWith({
        status: 'buffering',
        text: 'Hello world',
      });
    });

    it('should handle interrupted messages', () => {
      const messageId = 'test-message-123';
      const spy = vi.spyOn(ttsService as any, 'processQueue');
      
      ttsService.processStreamingText('Starting text', messageId);
      ttsService.interruptMessage(messageId);
      
      // Should not process more text for interrupted message
      spy.mockClear();
      ttsService.processStreamingText(' more text that has enough words to trigger processing.', messageId);
      expect(spy).not.toHaveBeenCalled();
    });
  });

  describe('provider switching and configuration', () => {
    it('should initialize with ElevenLabs as default provider', () => {
      expect(ttsService.getConfig().provider).toBe('elevenlabs');
      expect(ttsService.getConfig().elevenLabsApiKey).toBe('sk_c467a0c77dd236d4fac4a9cc7cbd5d2aad561771b7d3a18f');
    });

    it('should switch between providers correctly', async () => {
      // Start with ElevenLabs
      let voices = await ttsService.getVoices();
      expect(voices).toHaveLength(2);
      expect(voices[0].name).toBe('Rachel');
      
      // Switch to Browser
      ttsService.updateConfig({ provider: 'browser' });
      voices = await ttsService.getVoices();
      expect(voices).toHaveLength(2);
      expect(voices[0].name).toBe('Google US English');
      
      // Switch to macOS
      ttsService.updateConfig({ provider: 'macos' });
      voices = await ttsService.getVoices();
      expect(voices).toHaveLength(1);
      expect(voices[0].name).toBe('Samantha');
    });

    it('should save config changes to localStorage', () => {
      ttsService.updateConfig({
        provider: 'browser',
        voice: 'browser-voice-1',
        rate: 1.5,
        volume: 0.8,
      });
      
      expect(saveConfig).toHaveBeenCalledWith({
        ttsProvider: 'browser',
        ttsVoice: 'browser-voice-1',
        ttsRate: 1.5,
        ttsVolume: 0.8,
      });
    });

    it('should recreate ElevenLabs provider when API key changes', () => {
      const initialProvider = (ttsService as any).provider;
      
      ttsService.updateConfig({ elevenLabsApiKey: 'new-api-key' });
      
      const newProvider = (ttsService as any).provider;
      expect(newProvider).not.toBe(initialProvider);
      expect(saveConfig).toHaveBeenCalledWith(
        expect.objectContaining({ elevenLabsApiKey: 'new-api-key' })
      );
    });
  });

  describe('ElevenLabs integration', () => {
    it('should handle ElevenLabs TTS with correct voice', async () => {
      const provider = (ttsService as any).provider;
      
      // Process text with specific voice
      ttsService.updateConfig({ voice: '0NkECxcbkydDMspBKvQp' });
      ttsService.processStreamingText('Hello, this is a test message.');
      ttsService.finishStreaming();
      
      await vi.waitFor(() => {
        expect(provider.speak).toHaveBeenCalledWith(
          'Hello, this is a test message.',
          expect.objectContaining({
            voice: '0NkECxcbkydDMspBKvQp',
            rate: 1.0,
            volume: 1.0,
          })
        );
      });
    });

    it('should handle streaming text properly for ElevenLabs', async () => {
      const provider = (ttsService as any).provider;
      const stateListener = vi.fn();
      ttsService.onStateChange(stateListener);
      
      // Stream text in chunks
      ttsService.processStreamingText('Hello, this is');
      ttsService.processStreamingText(' a longer message');
      ttsService.processStreamingText(' that will be processed');
      ttsService.processStreamingText(' when it has enough words.');
      
      await vi.waitFor(() => {
        expect(provider.speak).toHaveBeenCalled();
      });
      
      // Check state transitions
      expect(stateListener).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'buffering' })
      );
      expect(stateListener).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'rendering' })
      );
      expect(stateListener).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'playing' })
      );
    });
  });

  describe('error handling', () => {
    it('should handle provider errors gracefully', async () => {
      const provider = (ttsService as any).provider;
      const stateListener = vi.fn();
      ttsService.onStateChange(stateListener);
      
      // Make provider throw error
      provider.speak.mockRejectedValueOnce(new Error('ElevenLabs API error'));
      
      ttsService.processStreamingText('This will fail.');
      ttsService.finishStreaming();
      
      await vi.waitFor(() => {
        expect(stateListener).toHaveBeenCalledWith({
          status: 'error',
          error: 'ElevenLabs API error',
        });
      });
    });

    it('should continue processing queue after error', async () => {
      const provider = (ttsService as any).provider;
      
      // First call fails, second succeeds
      provider.speak
        .mockRejectedValueOnce(new Error('Temporary error'))
        .mockResolvedValueOnce(undefined);
      
      ttsService.processStreamingText('First message.');
      ttsService.processStreamingText(' Second message.');
      ttsService.finishStreaming();
      
      await vi.waitFor(() => {
        expect(provider.speak).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('voice selection', () => {
    it('should get correct voices for each provider', async () => {
      // ElevenLabs voices
      let voices = await ttsService.getVoices();
      expect(voices).toEqual([
        { id: '0NkECxcbkydDMspBKvQp', name: 'Rachel', lang: 'en' },
        { id: 'elevenlabs-voice-2', name: 'Josh', lang: 'en' },
      ]);
      
      // Browser voices
      ttsService.setProvider('browser');
      voices = await ttsService.getVoices();
      expect(voices).toEqual([
        { id: 'browser-voice-1', name: 'Google US English', lang: 'en-US' },
        { id: 'browser-voice-2', name: 'Google UK English', lang: 'en-GB' },
      ]);
    });

    it('should use selected voice in TTS calls', async () => {
      const provider = (ttsService as any).provider;
      
      ttsService.updateConfig({ voice: 'elevenlabs-voice-2' });
      ttsService.processStreamingText('Test with Josh voice.');
      ttsService.finishStreaming();
      
      await vi.waitFor(() => {
        expect(provider.speak).toHaveBeenCalledWith(
          'Test with Josh voice.',
          expect.objectContaining({ voice: 'elevenlabs-voice-2' })
        );
      });
    });
  });
});