import { describe, it, expect, beforeEach, vi } from 'vitest';
import { BrowserSTTProvider } from './BrowserSTTProvider';

// Mock SpeechRecognition
class MockSpeechRecognition implements Partial<SpeechRecognition> {
  continuous = false;
  interimResults = false;
  lang = 'en-US';
  maxAlternatives = 1;
  
  onstart: (() => void) | null = null;
  onresult: ((event: any) => void) | null = null;
  onerror: ((event: any) => void) | null = null;
  onend: (() => void) | null = null;
  onsoundstart: (() => void) | null = null;
  onspeechstart: (() => void) | null = null;
  onaudiostart: (() => void) | null = null;
  onnomatch: (() => void) | null = null;
  onsoundend: (() => void) | null = null;
  onspeechend: (() => void) | null = null;
  
  start = vi.fn(() => {
    console.log('MockSpeechRecognition.start() called');
    // Simulate the start event
    setTimeout(() => {
      if (this.onstart) this.onstart();
      if (this.onaudiostart) this.onaudiostart();
    }, 10);
  });
  
  stop = vi.fn(() => {
    console.log('MockSpeechRecognition.stop() called');
    setTimeout(() => {
      if (this.onend) this.onend();
    }, 10);
  });
  
  abort = vi.fn();
}

describe('BrowserSTTProvider', () => {
  beforeEach(() => {
    // Setup mocks - using global window object from jsdom
    Object.defineProperty(window, 'SpeechRecognition', {
      writable: true,
      value: MockSpeechRecognition
    });
    
    Object.defineProperty(window, 'webkitSpeechRecognition', {
      writable: true,
      value: MockSpeechRecognition
    });
    
    // Mock getUserMedia with proper stream object
    global.navigator.mediaDevices = {
      getUserMedia: vi.fn().mockResolvedValue({
        getTracks: () => [{
          stop: vi.fn()
        }]
      })
    } as any;
    
    vi.clearAllMocks();
  });
  
  it('should create provider instance', () => {
    const provider = new BrowserSTTProvider('en-US', true, true);
    expect(provider).toBeDefined();
    expect(provider.name).toBe('Browser Speech Recognition');
  });
  
  it('should request microphone permission on start', async () => {
    const provider = new BrowserSTTProvider();
    await provider.startRecording();
    
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ 
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });
  });
  
  it('should call recognition.start() after getting microphone permission', async () => {
    const provider = new BrowserSTTProvider();
    await provider.startRecording();
    
    // Get the recognition instance
    const recognition = (provider as any).recognition;
    expect(recognition.start).toHaveBeenCalled();
  });
  
  it('should handle speech results', async () => {
    const provider = new BrowserSTTProvider();
    const interimCallback = vi.fn();
    provider.onInterimResult = interimCallback;
    
    await provider.startRecording();
    
    // Get the recognition instance and simulate result
    const recognition = (provider as any).recognition;
    const mockEvent = {
      resultIndex: 0,
      results: [
        { 0: { transcript: 'hello' }, isFinal: false },
        { 0: { transcript: 'world' }, isFinal: true }
      ]
    };
    
    // Trigger the onresult handler
    if (recognition.onresult) {
      recognition.onresult(mockEvent);
    }
    
    // With the new implementation in non-continuous mode, it accumulates final + interim
    // Based on the logs: all: "hello" final: "world" interim: "hello"
    // The callback is called with allTranscript which is "hello" in this case
    expect(interimCallback).toHaveBeenCalledWith('hello');
  });
  
  it('should reuse the same recognition instance', async () => {
    const provider = new BrowserSTTProvider();
    
    // Start first time
    await provider.startRecording();
    const firstRecognition = (provider as any).recognition;
    
    // Stop
    await provider.stopRecording();
    
    // Start again
    await provider.startRecording();
    const secondRecognition = (provider as any).recognition;
    
    // Should be the same instance (we don't recreate it anymore)
    expect(firstRecognition).toBe(secondRecognition);
  });
  
  it('should handle no-speech error gracefully', async () => {
    const provider = new BrowserSTTProvider();
    await provider.startRecording();
    
    const recognition = (provider as any).recognition;
    
    // Create promise to track stopRecording
    const stopPromise = provider.stopRecording();
    
    // Simulate no-speech error
    if (recognition.onerror) {
      recognition.onerror({ error: 'no-speech' });
    }
    
    // Should resolve with empty string
    const result = await stopPromise;
    expect(result).toBe('');
  });
});