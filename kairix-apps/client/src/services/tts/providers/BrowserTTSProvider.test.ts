import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { BrowserTTSProvider } from './BrowserTTSProvider'

// Mock SpeechSynthesisUtterance
class MockSpeechSynthesisUtterance implements Partial<SpeechSynthesisUtterance> {
  text = ''
  lang = 'en-US'
  voice: SpeechSynthesisVoice | null = null
  volume = 1
  rate = 1
  pitch = 1
  
  onstart: ((event: SpeechSynthesisEvent) => void) | null = null
  onend: ((event: SpeechSynthesisEvent) => void) | null = null
  onerror: ((event: SpeechSynthesisErrorEvent) => void) | null = null
  onpause: ((event: SpeechSynthesisEvent) => void) | null = null
  onresume: ((event: SpeechSynthesisEvent) => void) | null = null
  onmark: ((event: SpeechSynthesisEvent) => void) | null = null
  onboundary: ((event: SpeechSynthesisEvent) => void) | null = null
  
  constructor(text?: string) {
    if (text) this.text = text
  }
}

// Mock voices
const mockVoices: Partial<SpeechSynthesisVoice>[] = [
  {
    name: 'Google US English',
    lang: 'en-US',
    localService: true,
    default: true,
    voiceURI: 'Google US English'
  },
  {
    name: 'Google UK English Female',
    lang: 'en-GB',
    localService: true,
    default: false,
    voiceURI: 'Google UK English Female'
  },
  {
    name: 'Google español',
    lang: 'es-ES',
    localService: false,
    default: false,
    voiceURI: 'Google español'
  }
]

// Mock speechSynthesis
const mockSpeechSynthesis = {
  speak: vi.fn((utterance: any) => {
    // Simulate async speech
    setTimeout(() => {
      if (utterance.onstart) utterance.onstart(new Event('start'))
      setTimeout(() => {
        if (utterance.onend) utterance.onend(new Event('end'))
      }, 100)
    }, 10)
  }),
  cancel: vi.fn(),
  pause: vi.fn(),
  resume: vi.fn(),
  getVoices: vi.fn(() => mockVoices),
  pending: false,
  speaking: false,
  paused: false,
  onvoiceschanged: null,
  addEventListener: vi.fn((event: string, handler: any, options?: any) => {
    if (event === 'voiceschanged') {
      // Simulate voiceschanged event
      setTimeout(() => handler(new Event('voiceschanged')), 10)
    }
  }),
  removeEventListener: vi.fn()
}

describe('BrowserTTSProvider', () => {
  beforeEach(() => {
    // Setup mocks
    Object.defineProperty(window, 'speechSynthesis', {
      writable: true,
      value: mockSpeechSynthesis
    })
    
    Object.defineProperty(window, 'SpeechSynthesisUtterance', {
      writable: true,
      value: MockSpeechSynthesisUtterance
    })
    
    // Reset all mocks
    vi.clearAllMocks()
  })
  
  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('isSupported', () => {
    it('should return true when speechSynthesis is available', () => {
      const provider = new BrowserTTSProvider()
      expect(provider.isSupported()).toBe(true)
    })

    it('should return false when speechSynthesis is not available', () => {
      Object.defineProperty(window, 'speechSynthesis', {
        writable: true,
        value: undefined
      })
      
      const provider = new BrowserTTSProvider()
      expect(provider.isSupported()).toBe(false)
    })
  })

  describe('initialization', () => {
    it('should create provider instance', () => {
      const provider = new BrowserTTSProvider()
      expect(provider).toBeDefined()
      expect(provider.name).toBe('Browser Speech Synthesis')
    })
  })

  describe('getVoices', () => {
    it('should return available voices', async () => {
      const provider = new BrowserTTSProvider()
      const voices = await provider.getVoices()
      
      expect(voices).toHaveLength(3)
      expect(voices[0].name).toBe('Google US English')
      expect(voices[1].lang).toBe('en-GB')
      expect(voices[2].name).toBe('Google español')
    })

    it('should handle voice loading event', async () => {
      // Temporarily set getVoices to return empty array
      mockSpeechSynthesis.getVoices.mockReturnValueOnce([])
      
      const provider = new BrowserTTSProvider()
      const voicesPromise = provider.getVoices()
      
      // Simulate voiceschanged event
      if (mockSpeechSynthesis.onvoiceschanged) {
        mockSpeechSynthesis.getVoices.mockReturnValueOnce(mockVoices)
        mockSpeechSynthesis.onvoiceschanged(new Event('voiceschanged'))
      }
      
      const voices = await voicesPromise
      expect(voices).toHaveLength(3)
    })
  })

  describe('speak', () => {
    it('should speak text with default options', async () => {
      const provider = new BrowserTTSProvider()
      const text = 'Hello, world!'
      
      await provider.speak(text)
      
      expect(mockSpeechSynthesis.speak).toHaveBeenCalledTimes(1)
      const utterance = mockSpeechSynthesis.speak.mock.calls[0][0]
      expect(utterance.text).toBe(text)
      expect(utterance.lang).toBe('en-US')
      expect(utterance.rate).toBe(1)
      expect(utterance.pitch).toBe(1)
      expect(utterance.volume).toBe(1)
    })

    it('should apply custom options', async () => {
      const provider = new BrowserTTSProvider()
      const text = 'Test speech'
      const options = {
        voice: 'Google UK English Female',
        rate: 1.5,
        pitch: 0.8,
        volume: 0.7
      }
      
      await provider.speak(text, options)
      
      const utterance = mockSpeechSynthesis.speak.mock.calls[0][0]
      expect(utterance.text).toBe(text)
      expect(utterance.voice?.name).toBe('Google UK English Female')
      expect(utterance.rate).toBe(1.5)
      expect(utterance.pitch).toBe(0.8)
      expect(utterance.volume).toBe(0.7)
    })

    it('should use language-specific voice when specified by voiceURI', async () => {
      const provider = new BrowserTTSProvider()
      const text = 'Hola'
      
      await provider.speak(text, { voice: 'Google español' })
      
      const utterance = mockSpeechSynthesis.speak.mock.calls[0][0]
      expect(utterance.voice?.lang).toBe('es-ES')
    })

    it('should handle speech errors', async () => {
      const provider = new BrowserTTSProvider()
      
      // Mock speak to trigger error
      mockSpeechSynthesis.speak.mockImplementationOnce((utterance: any) => {
        setTimeout(() => {
          if (utterance.onerror) {
            const error = new Event('error') as any
            error.error = 'synthesis-failed'
            utterance.onerror(error)
          }
        }, 10)
      })
      
      await expect(provider.speak('Error test')).rejects.toThrow('synthesis-failed')
    })

    it('should cancel previous speech before starting new one', async () => {
      const provider = new BrowserTTSProvider()
      
      // Start first speech
      provider.speak('First speech')
      
      // Start second speech immediately
      await provider.speak('Second speech')
      
      expect(mockSpeechSynthesis.cancel).toHaveBeenCalledTimes(1)
      expect(mockSpeechSynthesis.speak).toHaveBeenCalledTimes(2)
    })

    it('should handle empty text gracefully', async () => {
      const provider = new BrowserTTSProvider()
      
      await provider.speak('')
      
      // Provider still creates utterance for empty text
      expect(mockSpeechSynthesis.speak).toHaveBeenCalled()
    })

    it('should handle undefined voice gracefully', async () => {
      const provider = new BrowserTTSProvider()
      
      await provider.speak('Test', { voice: 'Non-existent Voice' })
      
      const utterance = mockSpeechSynthesis.speak.mock.calls[0][0]
      expect(utterance.voice).toBeNull()
    })
  })

  describe('stop', () => {
    it('should cancel ongoing speech', () => {
      const provider = new BrowserTTSProvider()
      
      // Mock speaking state
      mockSpeechSynthesis.speaking = true
      
      provider.stop()
      
      expect(mockSpeechSynthesis.cancel).toHaveBeenCalledTimes(1)
    })

    it('should be safe to call multiple times', () => {
      const provider = new BrowserTTSProvider()
      
      // Mock speaking state
      mockSpeechSynthesis.speaking = true
      
      provider.stop()
      provider.stop()
      provider.stop()
      
      expect(mockSpeechSynthesis.cancel).toHaveBeenCalledTimes(3)
    })
  })

  describe('edge cases', () => {
    it('should handle rate limits', async () => {
      const provider = new BrowserTTSProvider()
      
      // Test rate boundaries
      await provider.speak('Test', { rate: 0.1 }) // Below normal range
      let utterance = mockSpeechSynthesis.speak.mock.calls[0][0]
      expect(utterance.rate).toBe(0.1)
      
      await provider.speak('Test', { rate: 10 }) // Above normal range
      utterance = mockSpeechSynthesis.speak.mock.calls[1][0]
      expect(utterance.rate).toBe(10)
    })

    it('should handle pitch limits', async () => {
      const provider = new BrowserTTSProvider()
      
      // Test pitch boundaries
      await provider.speak('Test', { pitch: 0 })
      let utterance = mockSpeechSynthesis.speak.mock.calls[0][0]
      expect(utterance.pitch).toBe(0)
      
      await provider.speak('Test', { pitch: 2 })
      utterance = mockSpeechSynthesis.speak.mock.calls[1][0]
      expect(utterance.pitch).toBe(2)
    })

    it('should handle volume limits', async () => {
      const provider = new BrowserTTSProvider()
      
      // Test volume boundaries
      await provider.speak('Test', { volume: 0 })
      let utterance = mockSpeechSynthesis.speak.mock.calls[0][0]
      expect(utterance.volume).toBe(0)
      
      await provider.speak('Test', { volume: 1 })
      utterance = mockSpeechSynthesis.speak.mock.calls[1][0]
      expect(utterance.volume).toBe(1)
    })
  })
})