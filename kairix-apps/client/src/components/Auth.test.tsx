import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { Auth } from './Auth'

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}))

describe('Auth Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('renders authentication form', () => {
    render(<Auth />)
    
    expect(screen.getByPlaceholderText('Enter access key')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument()
  })

  it('handles form submission with valid API key', async () => {
    const user = userEvent.setup()
    render(<Auth />)
    
    const input = screen.getByPlaceholderText('Enter access key')
    const submitButton = screen.getByRole('button', { name: /submit/i })
    
    await user.type(input, 'test-api-key-123')
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(localStorage.getItem('apiKey')).toBe('test-api-key-123')
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
  })

  it('requires API key before submission', async () => {
    const user = userEvent.setup()
    render(<Auth />)
    
    const submitButton = screen.getByRole('button', { name: /submit/i })
    
    // Try to submit without entering API key
    await user.click(submitButton)
    
    // Should not navigate or save to localStorage
    expect(localStorage.getItem('apiKey')).toBeNull()
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('trims whitespace from API key', async () => {
    const user = userEvent.setup()
    render(<Auth />)
    
    const input = screen.getByPlaceholderText('Enter access key')
    const submitButton = screen.getByRole('button', { name: /submit/i })
    
    await user.type(input, '  test-api-key-123  ')
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(localStorage.getItem('apiKey')).toBe('test-api-key-123')
    })
  })

  it('updates input value as user types', async () => {
    const user = userEvent.setup()
    render(<Auth />)
    
    const input = screen.getByPlaceholderText('Enter access key') as HTMLInputElement
    
    await user.type(input, 'my-api-key')
    
    expect(input.value).toBe('my-api-key')
  })

  it('allows form submission with Enter key', async () => {
    const user = userEvent.setup()
    render(<Auth />)
    
    const input = screen.getByPlaceholderText('Enter access key')
    
    await user.type(input, 'test-api-key-123')
    await user.type(input, '{Enter}')
    
    await waitFor(() => {
      expect(localStorage.getItem('apiKey')).toBe('test-api-key-123')
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
  })
})