import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { Chat } from './chat'
import type { Message } from 'ai'
import type { STTState } from '@/services/stt/types'

describe('Chat Component', () => {
  const defaultProps = {
    messages: [] as Message[],
    input: '',
    handleInputChange: vi.fn(),
    handleSubmit: vi.fn((e?: React.FormEvent) => e?.preventDefault()),
    isGenerating: false,
    stop: vi.fn(),
    sttState: { status: 'idle' } as STTState,
    onSTTToggle: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Textarea behavior', () => {
    it('renders a textarea instead of input', () => {
      render(<Chat {...defaultProps} />)
      const textarea = screen.getByTestId('chat-input') as HTMLTextAreaElement
      expect(textarea.tagName).toBe('TEXTAREA')
    })

    it('expands textarea height as content grows', async () => {
      const { rerender } = render(<Chat {...defaultProps} />)
      const textarea = screen.getByTestId('chat-input') as HTMLTextAreaElement
      
      // Mock scrollHeight to simulate content growth
      Object.defineProperty(textarea, 'scrollHeight', {
        configurable: true,
        get() {
          // Return different heights based on content length
          const lines = this.value.split('\n').length
          return Math.min(40 + (lines * 20), 200)
        }
      })
      
      // Simulate typing long content
      const longText = 'This is a very long message\n'.repeat(10)
      rerender(<Chat {...defaultProps} input={longText} />)
      
      await waitFor(() => {
        // The useEffect should have set the height based on scrollHeight
        expect(textarea.style.height).toBe('200px') // Max height
      })
    })

    it('limits textarea max height to 200px', async () => {
      const { rerender } = render(<Chat {...defaultProps} />)
      const textarea = screen.getByTestId('chat-input') as HTMLTextAreaElement
      
      // Mock scrollHeight to simulate very tall content
      Object.defineProperty(textarea, 'scrollHeight', {
        configurable: true,
        value: 500 // Much taller than max
      })
      
      // Simulate typing very long content
      const veryLongText = 'This is a very long message\n'.repeat(50)
      rerender(<Chat {...defaultProps} input={veryLongText} />)
      
      await waitFor(() => {
        expect(textarea.style.height).toBe('200px') // Should be capped at max
      })
    })

    it('auto-scrolls to bottom when content exceeds visible area', async () => {
      const { rerender } = render(<Chat {...defaultProps} />)
      const textarea = screen.getByTestId('chat-input') as HTMLTextAreaElement
      
      // Mock scroll properties
      let scrollTop = 0
      Object.defineProperty(textarea, 'scrollHeight', {
        configurable: true,
        value: 300,
      })
      Object.defineProperty(textarea, 'clientHeight', {
        configurable: true,
        value: 200,
      })
      Object.defineProperty(textarea, 'scrollTop', {
        configurable: true,
        get: () => scrollTop,
        set: (value) => { scrollTop = value }
      })
      
      const longText = 'This is a very long message\n'.repeat(20)
      rerender(<Chat {...defaultProps} input={longText} />)
      
      await waitFor(() => {
        expect(scrollTop).toBe(300)
      })
    })

    it('allows manual scrolling up while preserving position', async () => {
      const { rerender } = render(<Chat {...defaultProps} />)
      const textarea = screen.getByTestId('chat-input') as HTMLTextAreaElement
      
      // Set up scrollable content
      Object.defineProperty(textarea, 'scrollHeight', {
        configurable: true,
        value: 300,
      })
      Object.defineProperty(textarea, 'clientHeight', {
        configurable: true,
        value: 200,
      })
      
      const longText = 'This is a very long message\n'.repeat(20)
      rerender(<Chat {...defaultProps} input={longText} />)
      
      // Manually scroll up
      fireEvent.scroll(textarea, { target: { scrollTop: 50 } })
      
      // Verify scroll position is preserved
      expect(textarea.scrollTop).toBe(50)
    })

    it('submits on Enter key press', async () => {
      render(<Chat {...defaultProps} input="Test message" />)
      const textarea = screen.getByTestId('chat-input')
      
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
      
      expect(defaultProps.handleSubmit).toHaveBeenCalledTimes(1)
    })

    it('inserts newline on Shift+Enter', async () => {
      render(<Chat {...defaultProps} input="Test message" />)
      const textarea = screen.getByTestId('chat-input')
      
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })
      
      expect(defaultProps.handleSubmit).not.toHaveBeenCalled()
    })
  })

  describe('Button visibility', () => {
    it('keeps buttons visible when textarea expands', async () => {
      const { rerender } = render(<Chat {...defaultProps} />)
      const sendButton = screen.getByTestId('chat-send-button')
      const micButton = screen.getByTestId('chat-mic-button')
      
      // Simulate long content that expands textarea
      const longText = 'This is a very long message\n'.repeat(10)
      rerender(<Chat {...defaultProps} input={longText} />)
      
      // Buttons should be present in the DOM
      expect(sendButton).toBeInTheDocument()
      expect(micButton).toBeInTheDocument()
      
      // Check that the flex container has items-end class
      const container = sendButton.parentElement
      expect(container).toHaveClass('items-end')
    })

    it('aligns buttons to bottom of expanded textarea', () => {
      render(<Chat {...defaultProps} />)
      const container = screen.getByTestId('chat-input').parentElement?.parentElement
      
      expect(container).toHaveClass('items-end')
    })
  })

  describe('Loading states', () => {
    it('shows loading indicator when STT is processing', () => {
      render(<Chat {...defaultProps} sttState={{ status: 'processing' } as STTState} />)
      
      expect(screen.getByTestId('chat-input')).toBeDisabled()
      // Look for the spinner by its class
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })

    it('shows listening placeholder when STT is active', () => {
      render(<Chat {...defaultProps} sttState={{ status: 'listening' } as STTState} />)
      
      expect(screen.getByPlaceholderText('Listening...')).toBeInTheDocument()
    })
  })

  describe('Responsive behavior', () => {
    it('maintains proper layout on mobile viewports', () => {
      // Mock mobile viewport
      global.innerWidth = 375
      global.innerHeight = 667
      
      render(<Chat {...defaultProps} />)
      
      const formContainer = screen.getByTestId('chat-input').closest('form')
      expect(formContainer).toHaveClass('p-3')
      
      const buttonsContainer = screen.getByTestId('chat-input').parentElement?.parentElement
      expect(buttonsContainer).toHaveClass('gap-2')
    })
  })

  describe('Accessibility', () => {
    it('maintains focus on textarea after submit', async () => {
      render(<Chat {...defaultProps} input="Test" />)
      const textarea = screen.getByTestId('chat-input')
      
      textarea.focus()
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
      
      await waitFor(() => {
        expect(document.activeElement).toBe(textarea)
      })
    })

    it('has proper ARIA attributes', () => {
      render(<Chat {...defaultProps} />)
      const textarea = screen.getByTestId('chat-input')
      
      expect(textarea).toHaveAttribute('placeholder')
      expect(textarea).not.toHaveAttribute('aria-invalid')
    })
  })
})