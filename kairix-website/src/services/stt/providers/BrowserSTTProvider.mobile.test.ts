import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { BrowserSTTProvider } from './BrowserSTTProvider';

// Mock SpeechRecognition
const mockSpeechRecognition = vi.fn();
const mockStart = vi.fn();
const mockStop = vi.fn();
const mockAbort = vi.fn();

// Store original user agent
const originalUserAgent = navigator.userAgent;

describe('BrowserSTTProvider - Mobile Tests', () => {
  let provider: BrowserSTTProvider;
  let recognitionInstance: any;

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();

    // Create mock instance
    recognitionInstance = {
      start: mockStart,
      stop: mockStop,
      abort: mockAbort,
      continuous: undefined,
      interimResults: undefined,
      lang: undefined,
      maxAlternatives: undefined,
      onstart: null,
      onresult: null,
      onerror: null,
      onend: null,
    };

    mockSpeechRecognition.mockReturnValue(recognitionInstance);

    // Set up global mocks
    (global as any).SpeechRecognition = mockSpeechRecognition;
    (global as any).webkitSpeechRecognition = mockSpeechRecognition;

    // Mock getUserMedia
    global.navigator.mediaDevices = {
      getUserMedia: vi.fn().mockResolvedValue({
        getTracks: () => [{
          stop: vi.fn()
        }]
      })
    } as any;
  });

  afterEach(() => {
    // Restore original user agent
    Object.defineProperty(navigator, 'userAgent', {
      value: originalUserAgent,
      writable: true,
      configurable: true
    });
  });

  describe('Mobile Device Detection', () => {
    it.each([
      ['iPhone', 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'],
      ['iPad', 'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)'],
      ['Android', 'Mozilla/5.0 (Linux; Android 10; SM-G960U)'],
    ])('should detect %s as mobile and disable continuous mode', (device, userAgent) => {
      // Mock mobile user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: userAgent,
        writable: true,
        configurable: true
      });

      provider = new BrowserSTTProvider('en-US', true, true);

      // Should force continuous to false on mobile
      expect(recognitionInstance.continuous).toBe(false);
    });

    it('should respect continuous mode on desktop', () => {
      // Mock desktop user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        writable: true,
        configurable: true
      });

      provider = new BrowserSTTProvider('en-US', true, true);

      // Should keep continuous as true on desktop
      expect(recognitionInstance.continuous).toBe(true);
    });
  });

  describe('Interim Results on Mobile', () => {
    beforeEach(() => {
      // Mock mobile user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
        writable: true,
        configurable: true
      });

      provider = new BrowserSTTProvider('en-US', false, true);
    });

    it('should show interim results as user speaks on mobile', () => {
      const interimCallback = vi.fn();
      provider.onInterimResult = interimCallback;

      // Simulate speech recognition results
      const mockEvent = {
        results: [
          { 
            0: { transcript: 'hello' },
            isFinal: false,
            length: 1
          }
        ],
        length: 1
      };

      // Trigger onresult
      recognitionInstance.onresult(mockEvent);

      // Should call interim callback with current text
      expect(interimCallback).toHaveBeenCalledWith('hello');
    });

    it('should accumulate interim results on mobile', () => {
      const interimCallback = vi.fn();
      provider.onInterimResult = interimCallback;

      // First result
      recognitionInstance.onresult({
        results: [
          { 0: { transcript: 'hello' }, isFinal: false }
        ]
      });

      expect(interimCallback).toHaveBeenLastCalledWith('hello');

      // Second result (accumulating)
      recognitionInstance.onresult({
        results: [
          { 0: { transcript: 'hello' }, isFinal: false },
          { 0: { transcript: 'world' }, isFinal: false }
        ]
      });

      expect(interimCallback).toHaveBeenLastCalledWith('hello world');
    });

    it('should handle final results on mobile', () => {
      const interimCallback = vi.fn();
      provider.onInterimResult = interimCallback;

      recognitionInstance.onresult({
        results: [
          { 0: { transcript: 'hello' }, isFinal: false },
          { 0: { transcript: 'world' }, isFinal: true }
        ]
      });

      expect(interimCallback).toHaveBeenCalledWith('hello world');
    });
  });

  describe('Mobile-specific Error Handling', () => {
    beforeEach(() => {
      // Mock mobile user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
        writable: true,
        configurable: true
      });

      provider = new BrowserSTTProvider('en-US', false, true);
    });

    it('should handle no-speech error gracefully on mobile', async () => {
      await provider.startRecording();

      const stopPromise = provider.stopRecording();

      // Simulate no-speech error
      recognitionInstance.onerror({ error: 'no-speech' });

      const result = await stopPromise;
      expect(result).toBe('');
    });

    it('should add delay for mobile audio resource release', async () => {
      const setTimeoutSpy = vi.spyOn(global, 'setTimeout');

      await provider.startRecording();

      // Should have called setTimeout for mobile delay
      expect(setTimeoutSpy).toHaveBeenCalledWith(expect.any(Function), 100);
    });
  });

  describe('Touch Event Integration', () => {
    it('should handle rapid start/stop calls on mobile', async () => {
      // Mock mobile user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
        writable: true,
        configurable: true
      });

      provider = new BrowserSTTProvider('en-US', false, true);

      // First start
      await provider.startRecording();
      expect(mockStart).toHaveBeenCalledTimes(1);

      // Try to start again immediately - should throw
      await expect(provider.startRecording()).rejects.toThrow('Already recording');
      
      // Stop should work
      const stopPromise = provider.stopRecording();
      recognitionInstance.onend();
      await stopPromise;

      // Now can start again
      await provider.startRecording();
      expect(mockStart).toHaveBeenCalledTimes(2);
    });
  });
});