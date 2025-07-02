import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { Select } from './select'

describe('Select Component', () => {
  it('renders select element', () => {
    render(
      <Select>
        <option value="1">Option 1</option>
        <option value="2">Option 2</option>
      </Select>
    )
    
    const select = screen.getByRole('combobox')
    expect(select).toBeInTheDocument()
    expect(select.tagName).toBe('SELECT')
  })

  it('renders with options', () => {
    render(
      <Select>
        <option value="1">Option 1</option>
        <option value="2">Option 2</option>
        <option value="3">Option 3</option>
      </Select>
    )
    
    const options = screen.getAllByRole('option')
    expect(options).toHaveLength(3)
    expect(options[0]).toHaveTextContent('Option 1')
    expect(options[1]).toHaveTextContent('Option 2')
    expect(options[2]).toHaveTextContent('Option 3')
  })

  it('applies correct styling classes', () => {
    render(
      <Select>
        <option value="1">Option 1</option>
      </Select>
    )
    
    const select = screen.getByRole('combobox')
    expect(select).toHaveClass(
      'flex',
      'h-10',
      'w-full',
      'rounded-md',
      'border',
      'border-input',
      'bg-background',
      'px-3',
      'py-2',
      'text-sm'
    )
  })

  it('handles change events', async () => {
    const handleChange = vi.fn()
    const user = userEvent.setup()
    
    render(
      <Select onChange={handleChange} defaultValue="1">
        <option value="1">Option 1</option>
        <option value="2">Option 2</option>
      </Select>
    )
    
    const select = screen.getByRole('combobox')
    await user.selectOptions(select, '2')
    
    expect(handleChange).toHaveBeenCalledTimes(1)
    expect(select).toHaveValue('2')
  })

  it('can be disabled', () => {
    render(
      <Select disabled>
        <option value="1">Option 1</option>
      </Select>
    )
    
    const select = screen.getByRole('combobox')
    expect(select).toBeDisabled()
    expect(select).toHaveClass('disabled:cursor-not-allowed', 'disabled:opacity-50')
  })

  it('applies custom className', () => {
    render(
      <Select className="custom-select">
        <option value="1">Option 1</option>
      </Select>
    )
    
    const select = screen.getByRole('combobox')
    expect(select).toHaveClass('custom-select')
    expect(select).toHaveClass('flex') // Still has default classes
  })

  it('forwards ref correctly', () => {
    const ref = vi.fn()
    render(
      <Select ref={ref}>
        <option value="1">Option 1</option>
      </Select>
    )
    
    expect(ref).toHaveBeenCalled()
    expect(ref.mock.calls[0][0]).toBeInstanceOf(HTMLSelectElement)
  })

  it('passes through HTML select attributes', () => {
    render(
      <Select
        name="test-select"
        id="test-id"
        required
        multiple
      >
        <option value="1">Option 1</option>
      </Select>
    )
    
    const select = screen.getByRole('listbox') // multiple selects have listbox role
    expect(select).toHaveAttribute('name', 'test-select')
    expect(select).toHaveAttribute('id', 'test-id')
    expect(select).toBeRequired()
    expect(select).toHaveAttribute('multiple')
  })
})