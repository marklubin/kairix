import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { STTService } from './STTService';
import type { STTState } from './types';

// Store original user agent
const originalUserAgent = navigator.userAgent;

describe('STTService - Mobile Integration', () => {
  let sttService: STTService;
  let stateListener: vi.Mock;
  
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock mobile user agent
    Object.defineProperty(navigator, 'userAgent', {
      value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
      writable: true,
      configurable: true
    });
    
    // Mock WhisperMobileSTTProvider
    vi.mock('./providers/WhisperMobileSTTProvider', () => ({
      WhisperMobileSTTProvider: vi.fn().mockImplementation(() => ({
        name: 'Whisper Mobile',
        isSupported: vi.fn().mockReturnValue(true),
        startRecording: vi.fn().mockResolvedValue(undefined),
        stopRecording: vi.fn().mockResolvedValue('test transcript'),
        abort: vi.fn(),
        onInterimResult: undefined
      }))
    }));
    
    stateListener = vi.fn();
  });
  
  afterEach(() => {
    // Restore original user agent
    Object.defineProperty(navigator, 'userAgent', {
      value: originalUserAgent,
      writable: true,
      configurable: true
    });
    
    if (sttService) {
      sttService.abort();
    }
  });
  
  describe('mobile detection', () => {
    it('should detect mobile and use whisper-mobile provider', () => {
      sttService = new STTService();
      const config = sttService.getConfig();
      
      expect(config.provider).toBe('whisper-mobile');
    });
    
    it('should use browser provider on desktop', () => {
      // Mock desktop user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        writable: true,
        configurable: true
      });
      
      sttService = new STTService();
      const config = sttService.getConfig();
      
      expect(config.provider).toBe('browser');
    });
  });
  
  describe('mobile provider setup', () => {
    it('should set up interim result handler for mobile', () => {
      sttService = new STTService();
      sttService.onStateChange(stateListener);
      
      // Get the provider
      const provider = (sttService as any).provider;
      
      // Simulate interim result
      if (provider.onInterimResult) {
        provider.onInterimResult('Hello world');
      }
      
      expect(stateListener).toHaveBeenCalledWith({
        status: 'listening',
        interimTranscript: 'Hello world'
      });
    });
  });
  
  describe('mobile auto-submit behavior', () => {
    it('should disable auto-submit on mobile', () => {
      sttService = new STTService();
      
      expect(sttService.isAutoSubmitEnabled()).toBe(false);
    });
    
    it('should enable auto-submit on desktop', () => {
      // Mock desktop user agent
      Object.defineProperty(navigator, 'userAgent', {
        value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        writable: true,
        configurable: true
      });
      
      sttService = new STTService();
      
      expect(sttService.isAutoSubmitEnabled()).toBe(true);
    });
  });
  
  describe('mobile recording flow', () => {
    beforeEach(() => {
      sttService = new STTService();
      sttService.onStateChange(stateListener);
    });
    
    it('should handle full recording flow on mobile', async () => {
      // Start recording
      await sttService.startRecording();
      
      expect(stateListener).toHaveBeenCalledWith({ status: 'listening' });
      
      // Simulate interim results
      const provider = (sttService as any).provider;
      if (provider.onInterimResult) {
        provider.onInterimResult('Hello');
        provider.onInterimResult('Hello world');
      }
      
      expect(stateListener).toHaveBeenCalledWith({
        status: 'listening',
        interimTranscript: 'Hello'
      });
      expect(stateListener).toHaveBeenCalledWith({
        status: 'listening',
        interimTranscript: 'Hello world'
      });
      
      // Stop recording
      const transcript = await sttService.stopRecording();
      
      expect(stateListener).toHaveBeenCalledWith({ status: 'processing' });
      expect(stateListener).toHaveBeenCalledWith({
        status: 'transcribed',
        transcript: 'test transcript'
      });
      expect(transcript).toBe('test transcript');
    });
    
    it('should handle errors during mobile recording', async () => {
      const provider = (sttService as any).provider;
      provider.startRecording.mockRejectedValueOnce(new Error('Microphone permission denied'));
      
      await expect(sttService.startRecording()).rejects.toThrow('Microphone permission denied');
      
      expect(stateListener).toHaveBeenCalledWith({
        status: 'error',
        error: 'Microphone permission denied'
      });
    });
  });
  
  describe('provider switching', () => {
    it('should switch from mobile to desktop provider', () => {
      sttService = new STTService();
      
      // Verify initial mobile provider
      expect(sttService.getConfig().provider).toBe('whisper-mobile');
      
      // Switch to desktop provider
      sttService.setProvider('browser');
      
      expect(sttService.getConfig().provider).toBe('browser');
    });
    
    it('should maintain interim result handler after switching back to mobile', () => {
      sttService = new STTService();
      sttService.onStateChange(stateListener);
      
      // Switch to browser then back to mobile
      sttService.setProvider('browser');
      sttService.setProvider('whisper-mobile');
      
      // Get the new provider
      const provider = (sttService as any).provider;
      
      // Verify interim handler still works
      if (provider.onInterimResult) {
        provider.onInterimResult('Test');
      }
      
      expect(stateListener).toHaveBeenCalledWith({
        status: 'listening',
        interimTranscript: 'Test'
      });
    });
  });
  
  describe('mobile-specific edge cases', () => {
    beforeEach(() => {
      sttService = new STTService();
      sttService.onStateChange(stateListener);
    });
    
    it('should handle empty transcript on mobile', async () => {
      const provider = (sttService as any).provider;
      provider.stopRecording.mockResolvedValueOnce('');
      
      await sttService.startRecording();
      const transcript = await sttService.stopRecording();
      
      expect(transcript).toBe('');
      expect(stateListener).toHaveBeenCalledWith({ status: 'idle' });
    });
    
    it('should handle abort during mobile recording', async () => {
      await sttService.startRecording();
      
      sttService.abort();
      
      expect(stateListener).toHaveBeenCalledWith({ status: 'idle' });
    });
    
    it('should handle toggle recording on mobile', async () => {
      // First toggle - start
      const result1 = await sttService.toggleRecording();
      expect(result1).toBeNull();
      expect(stateListener).toHaveBeenCalledWith({ status: 'listening' });
      
      // Second toggle - stop
      const result2 = await sttService.toggleRecording();
      expect(result2).toBe('test transcript');
      expect(stateListener).toHaveBeenCalledWith({
        status: 'transcribed',
        transcript: 'test transcript'
      });
    });
  });
});