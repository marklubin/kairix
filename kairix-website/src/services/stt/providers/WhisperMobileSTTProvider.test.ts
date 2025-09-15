import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { WhisperMobileSTTProvider } from './WhisperMobileSTTProvider';

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

describe('WhisperMobileSTTProvider', () => {
  let provider: WhisperMobileSTTProvider;
  
  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();
    
    // Mock global objects
    global.AudioContext = MockAudioContext as any;
    global.MediaStream = MockMediaStream as any;
    
    // Mock getUserMedia
    global.navigator.mediaDevices = {
      getUserMedia: vi.fn().mockResolvedValue(new MockMediaStream())
    } as any;
    
    // Setup transcriber mock
    mockTranscriber.mockResolvedValue({ text: 'test transcript' });
    
    provider = new WhisperMobileSTTProvider();
  });
  
  afterEach(() => {
    provider.abort();
    vi.clearAllTimers();
    vi.restoreAllMocks();
  });
  
  describe('initialization', () => {
    it('should create provider instance', () => {
      expect(provider).toBeDefined();
      expect(provider.name).toBe('Whisper Mobile');
    });
    
    it('should check browser support correctly', () => {
      expect(provider.isSupported()).toBe(true);
      
      // Test without MediaRecorder
      const originalMediaRecorder = (global as any).MediaRecorder;
      delete (global as any).MediaRecorder;
      expect(provider.isSupported()).toBe(false);
      (global as any).MediaRecorder = originalMediaRecorder;
    });
    
    it('should initialize model on first use', async () => {
      const { pipeline } = await import('@xenova/transformers');
      
      await provider.initialize();
      
      expect(pipeline).toHaveBeenCalledWith(
        'automatic-speech-recognition',
        'Xenova/whisper-tiny.en',
        expect.objectContaining({
          quantized: true,
          progress_callback: expect.any(Function)
        })
      );
    });
    
    it('should not reinitialize if already initialized', async () => {
      const { pipeline } = await import('@xenova/transformers');
      
      await provider.initialize();
      await provider.initialize();
      
      expect(pipeline).toHaveBeenCalledTimes(1);
    });
  });
  
  describe('recording', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });
    
    afterEach(() => {
      vi.useRealTimers();
    });
    
    it('should start recording successfully', async () => {
      await provider.startRecording();
      
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000
        }
      });
    });
    
    it('should throw error if already recording', async () => {
      await provider.startRecording();
      
      await expect(provider.startRecording()).rejects.toThrow('Already recording');
    });
    
    it('should process audio chunks at intervals', async () => {
      const interimCallback = vi.fn();
      provider.onInterimResult = interimCallback;
      
      await provider.startRecording();
      
      // Simulate audio processing
      const audioContext = (provider as any).audioContext;
      const processor = audioContext.createScriptProcessor();
      
      // Simulate audio data
      const mockEvent = {
        inputBuffer: {
          getChannelData: () => new Float32Array([0.1, 0.2, 0.3])
        }
      };
      
      processor.onaudioprocess?.(mockEvent);
      
      // Fast forward just 2 seconds (one interval)
      vi.advanceTimersByTime(2000);
      
      // Wait for the promise to resolve
      await new Promise(resolve => setImmediate(resolve));
      
      expect(mockTranscriber).toHaveBeenCalled();
      expect(interimCallback).toHaveBeenCalledWith('test transcript');
      
      // Clean up interval
      provider.abort();
    });
    
    it('should handle errors during chunk processing', async () => {
      mockTranscriber.mockRejectedValueOnce(new Error('Processing error'));
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      await provider.startRecording();
      
      // Add audio data
      const audioContext = (provider as any).audioContext;
      const processor = audioContext.createScriptProcessor();
      const mockEvent = {
        inputBuffer: {
          getChannelData: () => new Float32Array([0.1, 0.2, 0.3])
        }
      };
      processor.onaudioprocess?.(mockEvent);
      
      // Fast forward to trigger chunk processing
      vi.advanceTimersByTime(2000);
      await new Promise(resolve => setImmediate(resolve));
      
      expect(consoleError).toHaveBeenCalledWith('Error processing audio chunk:', expect.any(Error));
      
      // Clean up
      provider.abort();
      consoleError.mockRestore();
    });
  });
  
  describe('stopping recording', () => {
    it('should stop recording and return final transcript', async () => {
      await provider.startRecording();
      
      // Add some audio data
      const audioContext = (provider as any).audioContext;
      const processor = audioContext.createScriptProcessor();
      const mockEvent = {
        inputBuffer: {
          getChannelData: () => new Float32Array([0.1, 0.2, 0.3])
        }
      };
      processor.onaudioprocess?.(mockEvent);
      
      // Mock transcriber to return transcript for final processing
      mockTranscriber.mockResolvedValueOnce({ text: 'test transcript' });
      
      const transcript = await provider.stopRecording();
      
      expect(transcript).toBe('test transcript');
      expect((provider as any).isRecording).toBe(false);
    });
    
    it('should throw error if not recording', async () => {
      await expect(provider.stopRecording()).rejects.toThrow('Not recording');
    });
    
    it('should cleanup resources after stopping', async () => {
      await provider.startRecording();
      
      const stream = (provider as any).stream;
      const audioContext = (provider as any).audioContext;
      const tracks = stream.getTracks();
      const stopSpy = tracks[0].stop;
      
      await provider.stopRecording();
      
      expect(stopSpy).toHaveBeenCalled();
      expect(audioContext.close).toHaveBeenCalled();
      expect((provider as any).stream).toBeNull();
      expect((provider as any).audioContext).toBeNull();
    });
  });
  
  describe('abort', () => {
    it('should abort recording and cleanup', async () => {
      await provider.startRecording();
      
      const stream = (provider as any).stream;
      const audioContext = (provider as any).audioContext;
      const tracks = stream.getTracks();
      const stopSpy = tracks[0].stop;
      
      provider.abort();
      
      expect(stopSpy).toHaveBeenCalled();
      expect(audioContext.close).toHaveBeenCalled();
      expect((provider as any).isRecording).toBe(false);
    });
    
    it('should handle abort when not recording', () => {
      expect(() => provider.abort()).not.toThrow();
    });
  });
  
  describe('edge cases', () => {
    it('should handle getUserMedia errors', async () => {
      navigator.mediaDevices.getUserMedia = vi.fn().mockRejectedValue(new Error('Permission denied'));
      
      await expect(provider.startRecording()).rejects.toThrow('Permission denied');
    });
    
    it('should handle empty audio buffer', async () => {
      await provider.startRecording();
      
      const transcript = await provider.stopRecording();
      
      // Should still work with empty buffer
      expect(transcript).toBe('');
    });
    
    it('should handle model loading errors', async () => {
      const { pipeline } = await import('@xenova/transformers');
      pipeline.mockRejectedValueOnce(new Error('Model load failed'));
      
      await expect(provider.initialize()).rejects.toThrow('Model load failed');
    });
  });
});