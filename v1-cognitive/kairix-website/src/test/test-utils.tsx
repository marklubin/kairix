import { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { HotkeyProvider } from '@/contexts/HotkeyContext'
import { TTSProvider } from '@/contexts/TTSContext'
import { STTProvider } from '@/contexts/STTContext'

interface AllTheProvidersProps {
  children: React.ReactNode
}

const AllTheProviders = ({ children }: AllTheProvidersProps) => {
  return (
    <BrowserRouter>
      <HotkeyProvider>
        <TTSProvider>
          <STTProvider>
            {children}
          </STTProvider>
        </TTSProvider>
      </HotkeyProvider>
    </BrowserRouter>
  )
}

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) => render(ui, { wrapper: AllTheProviders, ...options })

// re-export everything
export * from '@testing-library/react'

// override render method
export { customRender as render }