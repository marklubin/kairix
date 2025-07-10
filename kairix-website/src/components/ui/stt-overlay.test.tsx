import { render, screen, fireEvent } from '@testing-library/react';
import { STTOverlay } from './stt-overlay';
import type { STTState } from '@/services/stt/types';

describe('STTOverlay', () => {
  const mockOnStop = vi.fn();

  beforeEach(() => {
    mockOnStop.mockClear();
  });

  it('should not render when STT is idle', () => {
    const sttState: STTState = { status: 'idle' };
    const { container } = render(<STTOverlay sttState={sttState} onStop={mockOnStop} />);
    expect(container.firstChild).toBeNull();
  });

  it('should render overlay when listening', () => {
    const sttState: STTState = { status: 'listening' };
    render(<STTOverlay sttState={sttState} onStop={mockOnStop} />);
    
    expect(screen.getByText('Listening...')).toBeInTheDocument();
    expect(screen.getByText('Tap to stop and send')).toBeInTheDocument();
  });

  it('should display transcript when available', () => {
    const transcript = 'Hello world, this is a test';
    const sttState: STTState = { 
      status: 'listening', 
      interimTranscript: transcript 
    };
    render(<STTOverlay sttState={sttState} onStop={mockOnStop} />);
    
    expect(screen.getByText(transcript)).toBeInTheDocument();
    expect(screen.queryByText('Listening...')).not.toBeInTheDocument();
  });

  it('should show processing state', () => {
    const sttState: STTState = { status: 'processing' };
    render(<STTOverlay sttState={sttState} onStop={mockOnStop} />);
    
    expect(screen.getByText('Processing...')).toBeInTheDocument();
    
    // Button should be disabled
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('should call onStop when button is clicked', () => {
    const sttState: STTState = { status: 'listening' };
    render(<STTOverlay sttState={sttState} onStop={mockOnStop} />);
    
    const button = screen.getByRole('button');
    fireEvent.click(button);
    
    expect(mockOnStop).toHaveBeenCalledTimes(1);
  });

  it('should not call onStop when button is disabled', () => {
    const sttState: STTState = { status: 'processing' };
    render(<STTOverlay sttState={sttState} onStop={mockOnStop} />);
    
    const button = screen.getByRole('button');
    fireEvent.click(button);
    
    expect(mockOnStop).not.toHaveBeenCalled();
  });

  it('should have dark overlay background', () => {
    const sttState: STTState = { status: 'listening' };
    render(<STTOverlay sttState={sttState} onStop={mockOnStop} />);
    
    const overlay = screen.getByText('Listening...').closest('.fixed');
    expect(overlay).toHaveClass('bg-black/80');
  });

  it('should display long transcripts properly', () => {
    const longTranscript = 'This is a very long transcript that contains multiple sentences. It should be displayed properly in the overlay. The text should be centered and readable.';
    const sttState: STTState = { 
      status: 'listening', 
      interimTranscript: longTranscript 
    };
    render(<STTOverlay sttState={sttState} onStop={mockOnStop} />);
    
    expect(screen.getByText(longTranscript)).toBeInTheDocument();
    expect(screen.getByText(longTranscript)).toHaveClass('text-center');
  });
});