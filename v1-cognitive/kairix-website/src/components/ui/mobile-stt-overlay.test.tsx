import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MobileSTTOverlay } from './mobile-stt-overlay';
import type { STTState } from '@/services/stt/types';

describe('MobileSTTOverlay', () => {
  const mockOnStop = vi.fn();
  
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });
  
  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });
  
  describe('rendering', () => {
    it('should not render when STT is idle', () => {
      const sttState: STTState = { status: 'idle' };
      const { container } = render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      expect(container.firstChild).toBeNull();
    });
    
    it('should render overlay when listening', () => {
      const sttState: STTState = { status: 'listening' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      expect(screen.getByText('Loading Whisper AI...')).toBeInTheDocument();
    });
    
    it('should render overlay when processing', () => {
      const sttState: STTState = { status: 'processing' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      expect(screen.getByText('Loading Whisper AI...')).toBeInTheDocument();
    });
  });
  
  describe('model loading', () => {
    it('should show loading state initially', () => {
      const sttState: STTState = { status: 'listening' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      expect(screen.getByText('Loading Whisper AI...')).toBeInTheDocument();
      expect(screen.getByText('Preparing speech recognition...')).toBeInTheDocument();
    });
    
    it('should transition to listening state after 2 seconds', async () => {
      const sttState: STTState = { status: 'listening' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      // Fast forward 2 seconds
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      
      expect(screen.getByText('Listening...')).toBeInTheDocument();
      expect(screen.queryByText('Loading Whisper AI...')).not.toBeInTheDocument();
    });
  });
  
  describe('transcript display', () => {
    it('should show placeholder when no transcript', () => {
      const sttState: STTState = { status: 'listening' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      // Wait for loading to complete
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      
      expect(screen.getByText('Start speaking...')).toBeInTheDocument();
    });
    
    it('should display interim transcript', () => {
      const transcript = 'Hello world, this is a test';
      const sttState: STTState = { 
        status: 'listening', 
        interimTranscript: transcript 
      };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      // Wait for loading to complete
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      
      expect(screen.getByText(transcript)).toBeInTheDocument();
    });
  });
  
  describe('waveform animation', () => {
    it('should animate waveform when listening', () => {
      const sttState: STTState = { status: 'listening' };
      const { container } = render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      // Wait for loading to complete
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      
      // Check for waveform bars
      const waveformBars = container.querySelectorAll('.w-1');
      expect(waveformBars.length).toBe(20);
      
      // Advance time to trigger animation
      act(() => {
        vi.advanceTimersByTime(100);
      });
      
      // Waveform should update
      const updatedBars = container.querySelectorAll('.w-1');
      updatedBars.forEach(bar => {
        expect(bar).toHaveStyle({ height: expect.stringMatching(/\d+px/) });
      });
    });
  });
  
  describe('stop button', () => {
    it('should not show stop button during loading', () => {
      const sttState: STTState = { status: 'listening' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      expect(screen.queryByText('Stop Recording')).not.toBeInTheDocument();
    });
    
    it('should show stop button after loading', () => {
      const sttState: STTState = { status: 'listening' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      // Wait for loading to complete
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      
      expect(screen.getByText('Stop Recording')).toBeInTheDocument();
    });
    
    it('should call onStop when button is touched', () => {
      const sttState: STTState = { status: 'listening' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      // Wait for loading to complete
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      
      const button = screen.getByRole('button');
      fireEvent.touchEnd(button);
      expect(mockOnStop).toHaveBeenCalledTimes(1);
    });
    
    it('should disable button when processing', () => {
      const sttState: STTState = { status: 'processing' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      // Wait for loading to complete
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      
      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
      expect(screen.getByText('Processing...')).toBeInTheDocument();
    });
  });
  
  describe('UI elements', () => {
    it('should have gradient background', () => {
      const sttState: STTState = { status: 'listening' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      const overlay = screen.getByText('Loading Whisper AI...').closest('.fixed');
      expect(overlay).toHaveClass('bg-gradient-to-b', 'from-black/90', 'to-black/95');
    });
    
    it('should show powered by text', () => {
      const sttState: STTState = { status: 'listening' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      expect(screen.getByText('Powered by Whisper AI')).toBeInTheDocument();
    });
    
    it('should show correct status text when listening', () => {
      const sttState: STTState = { status: 'listening' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      // Wait for loading to complete
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      
      expect(screen.getByText('Tap stop when you\'re done speaking')).toBeInTheDocument();
    });
    
    it('should show correct status text when processing', () => {
      const sttState: STTState = { status: 'processing' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      // Wait for loading to complete
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      
      expect(screen.getByText('Converting speech to text...')).toBeInTheDocument();
    });
  });
  
  describe('responsive behavior', () => {
    it('should have proper mobile padding', () => {
      const sttState: STTState = { status: 'listening' };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      const contentArea = screen.getByText('Loading Whisper AI...').closest('.flex-col');
      expect(contentArea).toHaveClass('px-6');
    });
    
    it('should handle long transcripts with scrolling', () => {
      const longTranscript = 'This is a very long transcript. '.repeat(20);
      const sttState: STTState = { 
        status: 'listening', 
        interimTranscript: longTranscript 
      };
      render(<MobileSTTOverlay sttState={sttState} onStop={mockOnStop} />);
      
      // Wait for loading to complete
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      
      const transcriptContainer = screen.getByText(longTranscript).parentElement;
      expect(transcriptContainer).toHaveClass('overflow-y-auto', 'max-h-[200px]');
    });
  });
});