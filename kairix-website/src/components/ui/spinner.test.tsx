import { render, screen } from '@testing-library/react'
import { Spinner } from './spinner'

describe('Spinner Component', () => {
  it('renders spinner SVG element', () => {
    render(<Spinner />)
    const spinner = screen.getByRole('img', { hidden: true })
    expect(spinner).toBeInTheDocument()
    expect(spinner.tagName).toBe('svg')
  })

  it('has correct default classes', () => {
    render(<Spinner />)
    const spinner = screen.getByRole('img', { hidden: true })
    expect(spinner).toHaveClass('animate-spin', 'h-5', 'w-5', 'mr-3')
  })

  it('applies custom className', () => {
    render(<Spinner className="custom-spinner" />)
    const spinner = screen.getByRole('img', { hidden: true })
    expect(spinner).toHaveClass('custom-spinner')
    expect(spinner).toHaveClass('animate-spin') // Still has default animation
  })

  it('renders with correct SVG structure', () => {
    const { container } = render(<Spinner />)
    const svg = container.querySelector('svg')
    const circle = svg?.querySelector('circle')
    const path = svg?.querySelector('path')
    
    expect(svg).toHaveAttribute('viewBox', '0 0 24 24')
    expect(circle).toHaveAttribute('cx', '12')
    expect(circle).toHaveAttribute('cy', '12')
    expect(circle).toHaveAttribute('r', '10')
    expect(path).toHaveAttribute('d', 'M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z')
  })
})