import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { WhisperUnifiedSTTProvider } from './WhisperUnifiedSTTProvider';

// Mock the transformers library
const mockTranscriber = vi.fn();
vi.mock('@xenova/transformers', () => ({
  pipeline: vi.fn(() => Promise.resolve(mockTranscriber)),
  env: {
    allowLocalModels: false,
    useBrowserCache: true
  }
}));

// Mock AudioContext
class MockAudioContext {
  sampleRate = 16000;
  state = 'running';
  createMediaStreamSource = vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn()
  }));
  createScriptProcessor = vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    onaudioprocess: null
  }));
  close = vi.fn();
  destination = {};
}

// Mock MediaStream
class MockMediaStream {
  getTracks = vi.fn(() => [{
    stop: vi.fn()
  }]);
}

describe('WhisperUnifiedSTTProvider', () => {
  let provider: WhisperUnifiedSTTProvider;
  
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    
    global.AudioContext = MockAudioContext as any;
    global.MediaStream = MockMediaStream as any;
    
    global.navigator.mediaDevices = {
      getUserMedia: vi.fn().mockResolvedValue(new MockMediaStream())
    } as any;
    
    mockTranscriber.mockResolvedValue({ text: 'test transcript' });
    
    provider = new WhisperUnifiedSTTProvider();
  });
  
  afterEach(() => {
    provider.abort();
    vi.clearAllTimers();
    vi.useRealTimers();
  });
  
  describe('text accumulation', () => {
    it('should accumulate text across multiple recordings', async () => {
      const interimCallback = vi.fn();
      provider.onInterimResult = interimCallback;
      
      // First recording
      await provider.startRecording();
      
      // Simulate audio data
      const audioContext = (provider as any).audioContext;
      const processor = audioContext.createScriptProcessor();
      const mockEvent = {
        inputBuffer: {
          getChannelData: () => new Float32Array([0.1, 0.2, 0.3])
        }
      };
      processor.onaudioprocess?.(mockEvent);
      
      // Wait for chunk processing
      vi.advanceTimersByTime(2000);
      await new Promise(resolve => setImmediate(resolve));
      
      const transcript1 = await provider.stopRecording();
      expect(transcript1).toBe('test transcript');
      
      // Second recording - should accumulate
      mockTranscriber.mockResolvedValue({ text: 'test transcript and more words' });
      
      await provider.startRecording();
      processor.onaudioprocess?.(mockEvent);
      vi.advanceTimersByTime(2000);
      await new Promise(resolve => setImmediate(resolve));
      
      const transcript2 = await provider.stopRecording();
      expect(transcript2).toBe('test transcript and more words');
      
      // Verify interim results showed accumulation
      expect(interimCallback).toHaveBeenCalledWith('test transcript');
      expect(interimCallback).toHaveBeenCalledWith('test transcript and more words');
    });
    
    it('should only clear transcript when explicitly called', async () => {
      // Set up initial transcript
      await provider.startRecording();
      mockTranscriber.mockResolvedValue({ text: 'initial text' });
      
      const audioContext = (provider as any).audioContext;
      const processor = audioContext.createScriptProcessor();
      processor.onaudioprocess?.({
        inputBuffer: {
          getChannelData: () => new Float32Array([0.1])
        }
      });
      
      vi.advanceTimersByTime(2000);
      await new Promise(resolve => setImmediate(resolve));
      await provider.stopRecording();
      
      // Start new recording without clearing
      await provider.startRecording();
      await provider.stopRecording();
      
      // Should still have the text
      expect((provider as any).accumulatedTranscript).toBe('initial text');
      
      // Now clear
      provider.clearTranscript();
      expect((provider as any).accumulatedTranscript).toBe('');
    });
    
    it('should handle continuous speech accumulation', async () => {
      const interimCallback = vi.fn();
      provider.onInterimResult = interimCallback;
      
      await provider.startRecording();
      
      const audioContext = (provider as any).audioContext;
      const processor = audioContext.createScriptProcessor();
      
      // Simulate continuous speech
      const phrases = [
        'Hello world',
        'Hello world this is a test',
        'Hello world this is a test of speech accumulation'
      ];
      
      for (const phrase of phrases) {
        mockTranscriber.mockResolvedValue({ text: phrase });
        processor.onaudioprocess?.({
          inputBuffer: {
            getChannelData: () => new Float32Array([0.1, 0.2])
          }
        });
        
        vi.advanceTimersByTime(2000);
        await new Promise(resolve => setImmediate(resolve));
        
        expect(interimCallback).toHaveBeenLastCalledWith(phrase);
      }
      
      const finalTranscript = await provider.stopRecording();
      expect(finalTranscript).toBe('Hello world this is a test of speech accumulation');
    });
  });
  
  describe('workflow tests', () => {
    it('should never auto-submit text', async () => {
      // This provider has no auto-submit functionality
      // It only accumulates text and returns it
      
      await provider.startRecording();
      
      const audioContext = (provider as any).audioContext;
      const processor = audioContext.createScriptProcessor();
      processor.onaudioprocess?.({
        inputBuffer: {
          getChannelData: () => new Float32Array([0.1])
        }
      });
      
      vi.advanceTimersByTime(2000);
      await new Promise(resolve => setImmediate(resolve));
      
      const transcript = await provider.stopRecording();
      
      // Provider just returns text, no submission
      expect(transcript).toBe('test transcript');
    });
    
    it('should support start/stop/start workflow', async () => {
      const interimCallback = vi.fn();
      provider.onInterimResult = interimCallback;
      
      // First session
      await provider.startRecording();
      vi.advanceTimersByTime(2000);
      await provider.stopRecording();
      
      // Second session - should work immediately
      await provider.startRecording();
      expect((provider as any).isRecording).toBe(true);
      
      await provider.stopRecording();
      expect((provider as any).isRecording).toBe(false);
    });
  });
  
  describe('error handling', () => {
    it('should handle microphone permission errors', async () => {
      navigator.mediaDevices.getUserMedia = vi.fn().mockRejectedValue(
        new Error('Permission denied')
      );
      
      await expect(provider.startRecording()).rejects.toThrow('Permission denied');
    });
    
    it('should handle transcription errors gracefully', async () => {
      const interimCallback = vi.fn();
      provider.onInterimResult = interimCallback;
      
      await provider.startRecording();
      
      // Make transcriber fail
      mockTranscriber.mockRejectedValueOnce(new Error('Model error'));
      
      const audioContext = (provider as any).audioContext;
      const processor = audioContext.createScriptProcessor();
      processor.onaudioprocess?.({
        inputBuffer: {
          getChannelData: () => new Float32Array([0.1])
        }
      });
      
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      vi.advanceTimersByTime(2000);
      await new Promise(resolve => setImmediate(resolve));
      
      expect(consoleError).toHaveBeenCalledWith('Error processing audio chunk:', expect.any(Error));
      
      consoleError.mockRestore();
    });
  });
});