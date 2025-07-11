import { renderHook, act, waitFor } from '@testing-library/react';
import { useCustomChat } from './useCustomChat';
import { useTTS } from './contexts/TTSContext';
import { useSTT } from './contexts/STTContext';
import type { STTState } from './services/stt/types';

// Mock the contexts
vi.mock('./contexts/TTSContext');
vi.mock('./contexts/STTContext');
vi.mock('./lib/config', () => ({
  KAIRIX_SERVER_URL: 'http://localhost:8888'
}));
vi.mock('./lib/storage', () => ({
  ChatStorage: {
    getSession: vi.fn(() => []),
    saveSession: vi.fn(),
    clearSession: vi.fn(),
    getContextMessages: vi.fn((messages) => messages.slice(-20))
  }
}));

// Mock fetch
global.fetch = vi.fn();

// Mock SpeechRecognition
(window as any).SpeechRecognition = vi.fn();
(window as any).webkitSpeechRecognition = vi.fn();

describe('useCustomChat STT Integration', () => {
  let mockTTSService: any;
  let mockSTTService: any;
  let mockSetInput: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();
    
    // Mock TTS
    mockTTSService = {
      processStreamingText: vi.fn(),
      finishStreaming: vi.fn(),
      interruptMessage: vi.fn(),
      startNewMessage: vi.fn(),
      stop: vi.fn()
    };
    
    (useTTS as ReturnType<typeof vi.fn>).mockReturnValue({
      ttsService: mockTTSService,
      isEnabled: true
    });

    // Mock STT
    mockSTTService = {
      startRecording: vi.fn(),
      stopRecording: vi.fn(),
      isAutoSubmitEnabled: vi.fn(() => true),
      resetState: vi.fn()
    };

    // Mock fetch for API calls
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      body: {
        getReader: () => ({
          read: vi.fn()
            .mockResolvedValueOnce({ 
              done: false, 
              value: new TextEncoder().encode('data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n')
            })
            .mockResolvedValueOnce({ done: true })
        })
      }
    });
  });

  describe('STT Toggle Behavior', () => {
    it('should start recording when STT is idle', async () => {
      const sttState: STTState = { status: 'idle' };
      
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState
      });

      const { result } = renderHook(() => useCustomChat());

      await act(async () => {
        await result.current.handleSTTToggle();
      });

      expect(mockSTTService.startRecording).toHaveBeenCalledTimes(1);
      expect(mockSTTService.stopRecording).not.toHaveBeenCalled();
    });

    it('should stop recording and auto-submit when STT is listening', async () => {
      const transcript = 'Hello, this is my test message';
      mockSTTService.stopRecording.mockResolvedValue(transcript);
      
      const sttState: STTState = { status: 'listening' };
      
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState
      });

      const { result } = renderHook(() => useCustomChat());

      // Spy on handleSubmit
      const handleSubmitSpy = vi.spyOn(result.current, 'handleSubmit');

      await act(async () => {
        await result.current.handleSTTToggle();
      });

      // Verify stop was called
      expect(mockSTTService.stopRecording).toHaveBeenCalledTimes(1);
      
      // Verify auto-submit was called with transcript
      await waitFor(() => {
        expect(handleSubmitSpy).toHaveBeenCalledWith(undefined, transcript);
      });
      
      // Verify it was called exactly once
      expect(handleSubmitSpy).toHaveBeenCalledTimes(1);
    });

    it('should clear input before submitting', async () => {
      const transcript = 'Test message';
      const existingInput = 'Old text that should be cleared';
      mockSTTService.stopRecording.mockResolvedValue(transcript);
      
      const sttState: STTState = { status: 'listening' };
      
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState
      });

      const { result } = renderHook(() => useCustomChat());
      
      // Set initial input
      act(() => {
        result.current.setInput(existingInput);
      });
      
      expect(result.current.input).toBe(existingInput);

      await act(async () => {
        await result.current.handleSTTToggle();
      });

      // Input should be cleared
      expect(result.current.input).toBe('');
    });

    it('should not submit if transcript is empty', async () => {
      mockSTTService.stopRecording.mockResolvedValue('');
      
      const sttState: STTState = { status: 'listening' };
      
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState
      });

      const { result } = renderHook(() => useCustomChat());
      const handleSubmitSpy = vi.spyOn(result.current, 'handleSubmit');

      await act(async () => {
        await result.current.handleSTTToggle();
      });

      expect(mockSTTService.stopRecording).toHaveBeenCalledTimes(1);
      expect(handleSubmitSpy).not.toHaveBeenCalled();
    });

    it('should not submit if auto-submit is disabled', async () => {
      const transcript = 'Test message';
      mockSTTService.stopRecording.mockResolvedValue(transcript);
      mockSTTService.isAutoSubmitEnabled.mockReturnValue(false);
      
      const sttState: STTState = { status: 'listening' };
      
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState
      });

      const { result } = renderHook(() => useCustomChat());
      const handleSubmitSpy = vi.spyOn(result.current, 'handleSubmit');

      await act(async () => {
        await result.current.handleSTTToggle();
      });

      expect(mockSTTService.stopRecording).toHaveBeenCalledTimes(1);
      expect(handleSubmitSpy).not.toHaveBeenCalled();
    });

    it('should handle STT errors gracefully', async () => {
      const error = new Error('Microphone permission denied');
      mockSTTService.startRecording.mockRejectedValue(error);
      
      const sttState: STTState = { status: 'idle' };
      
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState
      });

      // Mock alert
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      const { result } = renderHook(() => useCustomChat());

      await act(async () => {
        await result.current.handleSTTToggle();
      });

      expect(alertSpy).toHaveBeenCalledWith('Speech recognition error: Microphone permission denied');
      
      alertSpy.mockRestore();
    });

    it('should interrupt TTS when starting STT', async () => {
      const sttState: STTState = { status: 'idle' };
      
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState
      });

      const { result } = renderHook(() => useCustomChat());
      
      // Simulate having a current assistant message
      result.current.currentAssistantMessageIdRef.current = 'msg-123';

      await act(async () => {
        await result.current.handleSTTToggle();
      });

      expect(mockTTSService.interruptMessage).toHaveBeenCalledWith('msg-123');
      expect(mockSTTService.startRecording).toHaveBeenCalledWith('msg-123');
    });
  });

  describe('STT State Change Handler', () => {
    it('should update input with interim transcript', () => {
      const sttState: STTState = { 
        status: 'listening', 
        interimTranscript: 'Hello world' 
      };
      
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState
      });

      const { result } = renderHook(() => useCustomChat());
      
      expect(result.current.input).toBe('Hello world');
    });

    it('should auto-submit final transcript', async () => {
      const transcript = 'Final message';
      
      const { result, rerender } = renderHook(() => useCustomChat());

      // Start with listening state
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState: { status: 'listening' }
      });
      
      rerender();

      // Spy on handleSubmit through the ref
      const handleSubmitSpy = vi.fn();
      result.current.handleSubmitRef.current = handleSubmitSpy;

      // Update to transcribed state
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState: { status: 'transcribed', transcript }
      });

      // Trigger re-render with new state
      rerender();

      // Wait for auto-submit
      await waitFor(() => {
        expect(handleSubmitSpy).toHaveBeenCalledWith(undefined, transcript);
      }, { timeout: 300 });

      expect(mockSTTService.resetState).toHaveBeenCalled();
    });

    it('should not auto-submit if auto-submit is disabled', async () => {
      mockSTTService.isAutoSubmitEnabled.mockReturnValue(false);
      const transcript = 'Final message';
      
      const sttState: STTState = { status: 'transcribed', transcript };
      
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState
      });

      const { result } = renderHook(() => useCustomChat());
      const handleSubmitSpy = vi.spyOn(result.current, 'handleSubmit');

      // Wait a bit to ensure no submit happens
      await new Promise(resolve => setTimeout(resolve, 200));

      expect(handleSubmitSpy).not.toHaveBeenCalled();
      expect(result.current.input).toBe(transcript);
      expect(mockSTTService.resetState).toHaveBeenCalled();
    });
  });

  describe('Submit Edge Cases', () => {
    it('should prevent double submission', async () => {
      const transcript = 'Test message';
      mockSTTService.stopRecording.mockResolvedValue(transcript);
      
      const sttState: STTState = { status: 'listening' };
      
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState
      });

      const { result } = renderHook(() => useCustomChat());
      const handleSubmitSpy = vi.spyOn(result.current, 'handleSubmit');

      // Call handleSTTToggle twice rapidly
      await act(async () => {
        const promise1 = result.current.handleSTTToggle();
        const promise2 = result.current.handleSTTToggle();
        await Promise.all([promise1, promise2]);
      });

      // Should only submit once
      expect(handleSubmitSpy).toHaveBeenCalledTimes(1);
    });

    it('should handle network errors during submission', async () => {
      const transcript = 'Test message';
      mockSTTService.stopRecording.mockResolvedValue(transcript);
      
      // Mock fetch to fail
      (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));
      
      const sttState: STTState = { status: 'listening' };
      
      (useSTT as ReturnType<typeof vi.fn>).mockReturnValue({
        sttService: mockSTTService,
        sttState
      });

      const { result } = renderHook(() => useCustomChat());

      await act(async () => {
        await result.current.handleSTTToggle();
      });

      // Check that error message was added
      await waitFor(() => {
        const errorMessage = result.current.messages.find(msg => 
          msg.content.includes('Sorry, I encountered an error')
        );
        expect(errorMessage).toBeDefined();
      });
    });
  });
});