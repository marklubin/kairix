import { describe, it, expect, vi, beforeEach } from 'vitest';
import { STTService } from './STTService';
import type { STTState } from './types';

// Mock WhisperUnifiedSTTProvider
vi.mock('./providers/WhisperUnifiedSTTProvider', () => ({
  WhisperUnifiedSTTProvider: vi.fn().mockImplementation(() => ({
    name: 'Whisper Unified',
    isSupported: vi.fn().mockReturnValue(true),
    startRecording: vi.fn().mockResolvedValue(undefined),
    stopRecording: vi.fn().mockResolvedValue('accumulated text'),
    abort: vi.fn(),
    clearTranscript: vi.fn(),
    onInterimResult: undefined
  }))
}));

describe('STT Workflow - Text Accumulation and Manual Submit', () => {
  let sttService: STTService;
  let stateListener: vi.Mock;
  
  beforeEach(() => {
    vi.clearAllMocks();
    sttService = new STTService();
    stateListener = vi.fn();
    sttService.onStateChange(stateListener);
  });
  
  it('should use whisper-unified provider by default', () => {
    const config = sttService.getConfig();
    expect(config.provider).toBe('whisper-unified');
  });
  
  it('should never auto-submit', () => {
    expect(sttService.isAutoSubmitEnabled()).toBe(false);
  });
  
  describe('accumulation workflow', () => {
    it('should accumulate text across multiple recording sessions', async () => {
      const provider = (sttService as any).provider;
      
      // First recording
      provider.stopRecording.mockResolvedValueOnce('Hello world');
      
      await sttService.startRecording();
      expect(stateListener).toHaveBeenCalledWith({ status: 'listening' });
      
      const transcript1 = await sttService.stopRecording();
      expect(transcript1).toBe('Hello world');
      expect(stateListener).toHaveBeenCalledWith({ 
        status: 'transcribed', 
        transcript: 'Hello world' 
      });
      
      // Second recording - provider accumulates
      provider.stopRecording.mockResolvedValueOnce('Hello world this is more text');
      
      await sttService.startRecording();
      const transcript2 = await sttService.stopRecording();
      expect(transcript2).toBe('Hello world this is more text');
    });
    
    it('should stream interim results during recording', async () => {
      const provider = (sttService as any).provider;
      
      await sttService.startRecording();
      
      // Simulate interim results
      if (provider.onInterimResult) {
        provider.onInterimResult('Hello');
        expect(stateListener).toHaveBeenCalledWith({
          status: 'listening',
          interimTranscript: 'Hello'
        });
        
        provider.onInterimResult('Hello world');
        expect(stateListener).toHaveBeenCalledWith({
          status: 'listening',
          interimTranscript: 'Hello world'
        });
      }
      
      await sttService.stopRecording();
    });
    
    it('should clear transcript only when explicitly called', async () => {
      const provider = (sttService as any).provider;
      
      // Record some text
      provider.stopRecording.mockResolvedValueOnce('Some text');
      await sttService.startRecording();
      await sttService.stopRecording();
      
      // Clear transcript
      sttService.clearTranscript();
      
      expect(provider.clearTranscript).toHaveBeenCalled();
      expect(stateListener).toHaveBeenCalledWith({ 
        status: 'idle', 
        interimTranscript: undefined 
      });
    });
  });
  
  describe('user interaction flow', () => {
    it('should support complete voice input workflow', async () => {
      const provider = (sttService as any).provider;
      
      // User clicks mic button to start
      await sttService.startRecording();
      expect(stateListener).toHaveBeenCalledWith({ status: 'listening' });
      
      // User speaks - interim results stream
      if (provider.onInterimResult) {
        provider.onInterimResult('Testing voice');
        provider.onInterimResult('Testing voice input');
        provider.onInterimResult('Testing voice input workflow');
      }
      
      // User clicks stop button
      provider.stopRecording.mockResolvedValueOnce('Testing voice input workflow');
      const transcript = await sttService.stopRecording();
      
      expect(transcript).toBe('Testing voice input workflow');
      expect(stateListener).toHaveBeenCalledWith({
        status: 'transcribed',
        transcript: 'Testing voice input workflow'
      });
      
      // Text should be in input box, user must manually click send
      // No auto-submission happens
    });
    
    it('should handle multiple start/stop cycles', async () => {
      const provider = (sttService as any).provider;
      
      // First cycle
      await sttService.startRecording();
      provider.stopRecording.mockResolvedValueOnce('First part');
      await sttService.stopRecording();
      
      // Second cycle - continues from first
      await sttService.startRecording();
      provider.stopRecording.mockResolvedValueOnce('First part second part');
      await sttService.stopRecording();
      
      // Third cycle
      await sttService.startRecording();
      provider.stopRecording.mockResolvedValueOnce('First part second part third part');
      const finalTranscript = await sttService.stopRecording();
      
      expect(finalTranscript).toBe('First part second part third part');
    });
  });
  
  describe('error scenarios', () => {
    it('should handle recording errors gracefully', async () => {
      const provider = (sttService as any).provider;
      provider.startRecording.mockRejectedValueOnce(new Error('Mic access denied'));
      
      await expect(sttService.startRecording()).rejects.toThrow('Mic access denied');
      expect(stateListener).toHaveBeenCalledWith({
        status: 'error',
        error: 'Mic access denied'
      });
    });
    
    it('should handle stop errors gracefully', async () => {
      const provider = (sttService as any).provider;
      
      await sttService.startRecording();
      
      provider.stopRecording.mockRejectedValueOnce(new Error('Processing failed'));
      
      await expect(sttService.stopRecording()).rejects.toThrow('Processing failed');
      expect(stateListener).toHaveBeenCalledWith({
        status: 'error',
        error: 'Processing failed'
      });
    });
  });
});