import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { Button } from './button'

describe('Button Component', () => {
  it('renders with default variant and size', () => {
    render(<Button>Click me</Button>)
    const button = screen.getByRole('button', { name: 'Click me' })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('bg-primary')
  })

  it('renders with all variants', () => {
    const variants = ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'] as const
    
    variants.forEach(variant => {
      const { rerender } = render(<Button variant={variant}>Button</Button>)
      const button = screen.getByRole('button')
      
      if (variant === 'default') expect(button).toHaveClass('bg-primary')
      if (variant === 'destructive') expect(button).toHaveClass('bg-destructive')
      if (variant === 'outline') expect(button).toHaveClass('border-input')
      if (variant === 'secondary') expect(button).toHaveClass('bg-secondary')
      if (variant === 'ghost') expect(button).toHaveClass('hover:bg-accent')
      if (variant === 'link') expect(button).toHaveClass('underline-offset-4')
      
      rerender(<></>)
    })
  })

  it('renders with all sizes', () => {
    const sizes = ['default', 'sm', 'lg', 'icon'] as const
    
    sizes.forEach(size => {
      const { rerender } = render(<Button size={size}>Button</Button>)
      const button = screen.getByRole('button')
      
      if (size === 'default') expect(button).toHaveClass('h-10 px-4 py-2')
      if (size === 'sm') expect(button).toHaveClass('h-9')
      if (size === 'lg') expect(button).toHaveClass('h-11')
      if (size === 'icon') expect(button).toHaveClass('h-10 w-10')
      
      rerender(<></>)
    })
  })

  it('handles click events', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()
    
    render(<Button onClick={handleClick}>Click me</Button>)
    const button = screen.getByRole('button')
    
    await user.click(button)
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('can be disabled', () => {
    render(<Button disabled>Click me</Button>)
    const button = screen.getByRole('button')
    
    expect(button).toBeDisabled()
    expect(button).toHaveClass('disabled:pointer-events-none disabled:opacity-50')
  })

  it('renders as child component when asChild is true', () => {
    render(
      <Button asChild>
        <a href="/test">Link button</a>
      </Button>
    )
    
    const link = screen.getByRole('link', { name: 'Link button' })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/test')
    expect(link).toHaveClass('inline-flex')
  })

  it('applies custom className', () => {
    render(<Button className="custom-class">Button</Button>)
    const button = screen.getByRole('button')
    
    expect(button).toHaveClass('custom-class')
    expect(button).toHaveClass('bg-primary') // Still has default classes
  })

  it('forwards ref correctly', () => {
    const ref = vi.fn()
    render(<Button ref={ref}>Button</Button>)
    
    expect(ref).toHaveBeenCalled()
    expect(ref.mock.calls[0][0]).toBeInstanceOf(HTMLButtonElement)
  })
})