import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { TTSService } from './TTSService';
import type { TTSProvider } from './types';

// Mock the providers
vi.mock('./providers/BrowserTTSProvider', () => ({
  BrowserTTSProvider: vi.fn().mockImplementation(() => ({
    name: 'browser',
    speak: vi.fn().mockResolvedValue(undefined),
    stop: vi.fn(),
    getVoices: vi.fn().mockResolvedValue([]),
  })),
}));

vi.mock('./providers/ElevenLabsTTSProvider', () => ({
  ElevenLabsTTSProvider: vi.fn().mockImplementation(() => ({
    name: 'elevenlabs',
    speak: vi.fn().mockResolvedValue(undefined),
    stop: vi.fn(),
    getVoices: vi.fn().mockResolvedValue([]),
  })),
}));

describe('TTSService', () => {
  let ttsService: TTSService;
  let mockProvider: TTSProvider;

  beforeEach(() => {
    ttsService = new TTSService({ provider: 'browser' });
    // Get the mock provider
    mockProvider = (ttsService as any).provider;
  });

  afterEach(() => {
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
});