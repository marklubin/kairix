import { STTService } from './STTService';
import { BrowserSTTProvider } from './providers/BrowserSTTProvider';
import type { STTState } from './types';

vi.mock('./providers/BrowserSTTProvider');
vi.mock('./providers/WhisperSTTProvider');

describe('STTService', () => {
  let sttService: STTService;
  let mockProvider: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockProvider = {
      name: 'browser',
      startRecording: vi.fn(),
      stopRecording: vi.fn(),
      abort: vi.fn(),
      onInterimResult: undefined
    };
    
    (BrowserSTTProvider as ReturnType<typeof vi.fn>).mockImplementation(() => mockProvider);
    sttService = new STTService();
  });

  describe('initialization', () => {
    it('should initialize with default config', () => {
      const config = sttService.getConfig();
      expect(config.provider).toBe('browser');
      expect(config.language).toBe('en-US');
      expect(config.continuous).toBe(true);
      expect(config.interimResults).toBe(true);
      expect(config.autoSubmit).toBe(true);
    });

    it('should accept custom config', () => {
      const customService = new STTService({
        provider: 'whisper',
        language: 'es-ES',
        autoSubmit: false
      });
      
      const config = customService.getConfig();
      expect(config.provider).toBe('whisper');
      expect(config.language).toBe('es-ES');
      expect(config.autoSubmit).toBe(false);
    });
  });

  describe('state management', () => {
    it('should start with idle state', () => {
      expect(sttService.getState().status).toBe('idle');
    });

    it('should notify listeners on state change', () => {
      const listener = vi.fn();
      const unsubscribe = sttService.onStateChange(listener);
      
      sttService.resetState();
      
      expect(listener).toHaveBeenCalledWith({ status: 'idle' });
      
      unsubscribe();
      sttService.resetState();
      expect(listener).toHaveBeenCalledTimes(1);
    });
  });

  describe('recording', () => {
    it('should start recording', async () => {
      await sttService.startRecording();
      
      expect(mockProvider.startRecording).toHaveBeenCalled();
      expect(sttService.getState().status).toBe('listening');
    });

    it('should handle start recording errors', async () => {
      const error = new Error('Microphone permission denied');
      mockProvider.startRecording.mockRejectedValue(error);
      
      await expect(sttService.startRecording()).rejects.toThrow('Microphone permission denied');
      expect(sttService.getState().status).toBe('error');
      expect(sttService.getState().error).toBe('Microphone permission denied');
    });

    it('should stop recording and return transcript', async () => {
      const transcript = 'Hello world';
      mockProvider.stopRecording.mockResolvedValue(transcript);
      
      // Start first
      await sttService.startRecording();
      
      // Then stop
      const result = await sttService.stopRecording();
      
      expect(result).toBe(transcript);
      expect(sttService.getState().status).toBe('transcribed');
      expect(sttService.getState().transcript).toBe(transcript);
    });

    it('should handle stop recording errors', async () => {
      const error = new Error('Failed to process audio');
      mockProvider.stopRecording.mockRejectedValue(error);
      
      await sttService.startRecording();
      
      await expect(sttService.stopRecording()).rejects.toThrow('Failed to process audio');
      expect(sttService.getState().status).toBe('error');
    });

    it('should toggle recording', async () => {
      // Start
      await sttService.toggleRecording();
      expect(sttService.getState().status).toBe('listening');
      
      // Stop
      mockProvider.stopRecording.mockResolvedValue('test');
      const transcript = await sttService.toggleRecording();
      expect(transcript).toBe('test');
    });
  });

  describe('interim results', () => {
    it('should handle interim results from provider', async () => {
      const listener = vi.fn();
      sttService.onStateChange(listener);
      
      await sttService.startRecording();
      
      // Simulate interim result
      mockProvider.onInterimResult('Hello');
      
      expect(listener).toHaveBeenCalledWith({
        status: 'listening',
        interimTranscript: 'Hello'
      });
    });
  });

  describe('abort', () => {
    it('should abort recording', async () => {
      await sttService.startRecording();
      
      sttService.abort();
      
      expect(mockProvider.abort).toHaveBeenCalled();
      expect(sttService.getState().status).toBe('idle');
    });
  });

  describe('auto-submit', () => {
    it('should return true by default', () => {
      expect(sttService.isAutoSubmitEnabled()).toBe(true);
    });

    it('should respect config setting', () => {
      sttService.updateConfig({ autoSubmit: false });
      expect(sttService.isAutoSubmitEnabled()).toBe(false);
    });
  });
});