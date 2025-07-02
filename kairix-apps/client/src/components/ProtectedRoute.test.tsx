import { render, screen } from '@testing-library/react'
import { ProtectedRoute } from './ProtectedRoute'

describe('ProtectedRoute Component', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders children when API key exists', () => {
    localStorage.setItem('apiKey', 'test-api-key')
    
    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    )
    
    expect(screen.getByText('Protected Content')).toBeInTheDocument()
    expect(screen.queryByText(/ahoy, matey/i)).not.toBeInTheDocument()
  })

  it('renders PirateShip when no API key', () => {
    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    )
    
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    expect(screen.getByText(/ahoy, matey/i)).toBeInTheDocument()
  })

  it('handles empty API key as unauthenticated', () => {
    localStorage.setItem('apiKey', '')
    
    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    )
    
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    expect(screen.getByText(/ahoy, matey/i)).toBeInTheDocument()
  })

  it('handles whitespace-only API key as unauthenticated', () => {
    localStorage.setItem('apiKey', '   ')
    
    render(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>
    )
    
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    expect(screen.getByText(/ahoy, matey/i)).toBeInTheDocument()
  })
})