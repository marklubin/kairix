import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import ChatContainer from './Chat'
import { TTSProvider } from './contexts/TTSContext'
import { STTProvider } from './contexts/STTContext'
import { HotkeyProvider } from './contexts/HotkeyContext'

// Mock the audio APIs
global.Audio = vi.fn().mockImplementation(() => ({
  play: vi.fn().mockResolvedValue(undefined),
  pause: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  currentTime: 0,
  volume: 1,
  playbackRate: 1,
}))

global.MediaRecorder = vi.fn().mockImplementation(() => ({
  start: vi.fn(),
  stop: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  state: 'inactive',
}))

global.navigator.mediaDevices = {
  getUserMedia: vi.fn().mockResolvedValue({
    getTracks: () => [],
  }),
}

// Mock fetch for ElevenLabs API
global.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: async () => ({ voices: [] }),
  text: async () => '',
  arrayBuffer: async () => new ArrayBuffer(0),
})

// Mock import.meta.env
vi.stubGlobal('import.meta.env', {
  VITE_API_URL: 'http://localhost:8888',
  VITE_KAIRIX_WEBSITE_PORT: '5173'
})

const renderChat = () => {
  return render(
    <HotkeyProvider>
      <TTSProvider>
        <STTProvider>
          <ChatContainer />
        </STTProvider>
      </TTSProvider>
    </HotkeyProvider>
  )
}

describe('TTS/STT Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('TTS UI Controls', () => {
    it('should show TTS settings when settings panel is opened', async () => {
      renderChat()
      
      // Open settings
      const settingsButton = screen.getByRole('button', { name: /settings/i })
      await userEvent.click(settingsButton)
      
      // Check TTS controls are visible
      expect(screen.getByText('TTS')).toBeInTheDocument()
      expect(screen.getByRole('checkbox')).toBeInTheDocument()
    })

    it('should show provider dropdown when TTS is enabled', async () => {
      renderChat()
      
      // Open settings
      const settingsButton = screen.getByRole('button', { name: /settings/i })
      await userEvent.click(settingsButton)
      
      // Enable TTS if not already enabled
      const ttsCheckbox = screen.getByRole('checkbox')
      if (!ttsCheckbox.checked) {
        await userEvent.click(ttsCheckbox)
      }
      
      // Check provider dropdown
      const providerSelect = screen.getByLabelText('Provider')
      expect(providerSelect).toBeInTheDocument()
      expect(providerSelect).toHaveValue('elevenlabs') // Default provider
      
      // Check available options
      const options = screen.getAllByRole('option')
      expect(options).toHaveLength(3)
      expect(options[0]).toHaveTextContent('Browser TTS')
      expect(options[1]).toHaveTextContent('ElevenLabs')
      expect(options[2]).toHaveTextContent('macOS')
    })

    it('should show ElevenLabs API key input when ElevenLabs is selected', async () => {
      renderChat()
      
      // Open settings and enable TTS
      const settingsButton = screen.getByRole('button', { name: /settings/i })
      await userEvent.click(settingsButton)
      
      const ttsCheckbox = screen.getByRole('checkbox')
      if (!ttsCheckbox.checked) {
        await userEvent.click(ttsCheckbox)
      }
      
      // Select ElevenLabs provider
      const providerSelect = screen.getByLabelText('Provider')
      await userEvent.selectOptions(providerSelect, 'elevenlabs')
      
      // Check API key input is visible
      const apiKeyInput = screen.getByLabelText('ElevenLabs API Key')
      expect(apiKeyInput).toBeInTheDocument()
      expect(apiKeyInput).toHaveAttribute('type', 'password')
    })

    it('should load and display voices for selected provider', async () => {
      // Mock ElevenLabs voices API
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          voices: [
            { voice_id: 'voice1', name: 'Rachel', labels: { language: 'en' } },
            { voice_id: 'voice2', name: 'Josh', labels: { language: 'en' } },
          ]
        })
      })
      
      renderChat()
      
      // Open settings and enable TTS
      const settingsButton = screen.getByRole('button', { name: /settings/i })
      await userEvent.click(settingsButton)
      
      const ttsCheckbox = screen.getByRole('checkbox')
      if (!ttsCheckbox.checked) {
        await userEvent.click(ttsCheckbox)
      }
      
      // Wait for voices to load
      await waitFor(() => {
        const voiceSelect = screen.getByLabelText('Voice')
        expect(voiceSelect).toBeInTheDocument()
      })
      
      // Check voice options
      const voiceSelect = screen.getByLabelText('Voice')
      const voiceOptions = voiceSelect.querySelectorAll('option')
      expect(voiceOptions).toHaveLength(3) // Default + 2 voices
      expect(voiceOptions[0]).toHaveTextContent('Default Voice')
      expect(voiceOptions[1]).toHaveTextContent('Rachel')
      expect(voiceOptions[2]).toHaveTextContent('Josh')
    })
  })

  describe('STT Input Clearing', () => {
    it('should clear input after STT auto-submission', async () => {
      renderChat()
      
      // Mock STT service
      const mockSpeechRecognition = {
        start: vi.fn(),
        stop: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }
      
      window.SpeechRecognition = vi.fn(() => mockSpeechRecognition)
      
      // Get chat input
      const chatInput = screen.getByPlaceholderText(/type.*message/i)
      
      // Simulate STT result
      fireEvent.change(chatInput, { target: { value: 'Test message from STT' } })
      expect(chatInput).toHaveValue('Test message from STT')
      
      // Simulate auto-submit
      const form = chatInput.closest('form')
      fireEvent.submit(form!)
      
      // Check input is cleared
      await waitFor(() => {
        expect(chatInput).toHaveValue('')
      })
    })
  })

  describe('TTS/STT Status Indicators', () => {
    it('should show correct TTS status indicator', async () => {
      renderChat()
      
      // Check TTS indicator
      const ttsIndicator = screen.getByText('TTS').nextElementSibling
      expect(ttsIndicator).toHaveClass('bg-gray-400') // Default idle state
    })

    it('should show correct STT status indicator', async () => {
      renderChat()
      
      // Check STT indicator
      const sttIndicator = screen.getByText('STT').nextElementSibling
      expect(sttIndicator).toHaveClass('bg-gray-400') // Default idle state
    })
  })

  describe('End-to-End TTS Flow', () => {
    it('should play TTS audio when message is received', async () => {
      // Mock ElevenLabs TTS API
      const audioBlob = new Blob(['mock audio data'], { type: 'audio/mpeg' })
      fetch.mockImplementation((url) => {
        if (url.includes('text-to-speech')) {
          return Promise.resolve({
            ok: true,
            arrayBuffer: async () => audioBlob.arrayBuffer()
          })
        }
        return Promise.resolve({ ok: false })
      })
      
      const mockAudioPlay = vi.fn().mockResolvedValue(undefined)
      global.Audio = vi.fn().mockImplementation(() => ({
        play: mockAudioPlay,
        pause: vi.fn(),
        addEventListener: vi.fn((event, handler) => {
          if (event === 'ended') {
            // Simulate audio ending after 100ms
            setTimeout(handler, 100)
          }
        }),
        removeEventListener: vi.fn(),
        currentTime: 0,
        volume: 1,
        playbackRate: 1,
      }))
      
      renderChat()
      
      // Enable TTS
      const settingsButton = screen.getByRole('button', { name: /settings/i })
      await userEvent.click(settingsButton)
      
      const ttsCheckbox = screen.getByRole('checkbox')
      if (!ttsCheckbox.checked) {
        await userEvent.click(ttsCheckbox)
      }
      
      // Close settings
      await userEvent.click(screen.getByText('×'))
      
      // Send a message to trigger response
      const chatInput = screen.getByPlaceholderText(/type.*message/i)
      await userEvent.type(chatInput, 'Hello')
      
      const form = chatInput.closest('form')
      fireEvent.submit(form!)
      
      // Wait for TTS to be triggered
      await waitFor(() => {
        expect(mockAudioPlay).toHaveBeenCalled()
      }, { timeout: 5000 })
    })
  })
})