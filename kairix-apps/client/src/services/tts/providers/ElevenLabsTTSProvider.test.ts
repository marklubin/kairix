import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { ElevenLabsTTSProvider } from './ElevenLabsTTSProvider'

// Mock fetch
global.fetch = vi.fn()

// Mock Audio
class MockAudio {
  src = ''
  volume = 1
  onended: (() => void) | null = null
  onerror: ((error: any) => void) | null = null
  
  play = vi.fn(() => {
    // Simulate async playback
    setTimeout(() => {
      if (this.onended) this.onended()
    }, 100)
    return Promise.resolve()
  })
  
  pause = vi.fn()
  
  addEventListener = vi.fn((event: string, handler: any) => {
    if (event === 'ended') this.onended = handler
    if (event === 'error') this.onerror = handler
  })
  
  removeEventListener = vi.fn()
}

// Mock URL.createObjectURL and revokeObjectURL
const mockObjectUrls = new Set<string>()
const originalCreateObjectURL = URL.createObjectURL
const originalRevokeObjectURL = URL.revokeObjectURL

describe('ElevenLabsTTSProvider', () => {
  beforeEach(() => {
    // Setup mocks
    vi.clearAllMocks()
    mockObjectUrls.clear()
    
    // Mock Audio constructor
    global.Audio = MockAudio as any
    
    // Mock URL methods
    URL.createObjectURL = vi.fn((blob: Blob) => {
      const url = `blob:mock-url-${Date.now()}`
      mockObjectUrls.add(url)
      return url
    })
    
    URL.revokeObjectURL = vi.fn((url: string) => {
      mockObjectUrls.delete(url)
    })
    
    // Mock successful fetch by default
    ;(global.fetch as any).mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(new Blob(['mock-audio-data'], { type: 'audio/mpeg' }))
    })
  })
  
  afterEach(() => {
    vi.clearAllTimers()
    URL.createObjectURL = originalCreateObjectURL
    URL.revokeObjectURL = originalRevokeObjectURL
  })

  describe('initialization', () => {
    it('should create provider instance with API key', () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      expect(provider).toBeDefined()
      expect(provider.name).toBe('ElevenLabs')
    })
    
    it('should create provider instance without API key', () => {
      const provider = new ElevenLabsTTSProvider('')
      expect(provider).toBeDefined()
      expect(provider.name).toBe('ElevenLabs')
    })
  })

  describe('isSupported', () => {
    it('should always return true', () => {
      const provider = new ElevenLabsTTSProvider('test-key')
      expect(provider.isSupported()).toBe(true)
    })
  })

  describe('getVoices', () => {
    it('should fetch voices from API', async () => {
      const mockVoices = {
        voices: [
          { voice_id: 'voice1', name: 'Voice 1' },
          { voice_id: 'voice2', name: 'Voice 2' }
        ]
      }
      
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockVoices)
      })
      
      const provider = new ElevenLabsTTSProvider('test-api-key')
      const voices = await provider.getVoices()
      
      expect(fetch).toHaveBeenCalledWith(
        'https://api.elevenlabs.io/v1/voices',
        expect.objectContaining({
          headers: {
            'xi-api-key': 'test-api-key'
          }
        })
      )
      
      expect(voices).toEqual([
        { voice_id: 'voice1', name: 'Voice 1' },
        { voice_id: 'voice2', name: 'Voice 2' }
      ])
    })
    
    it('should handle API errors when fetching voices', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized'
      })
      
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      await expect(provider.getVoices()).rejects.toThrow('Failed to fetch voices: 401 Unauthorized')
    })
  })

  describe('speak', () => {
    it('should synthesize speech with default options', async () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      const text = 'Hello, world!'
      
      await provider.speak(text)
      
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('https://api.elevenlabs.io/v1/text-to-speech/'),
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'xi-api-key': 'test-api-key'
          },
          body: JSON.stringify({
            text,
            model_id: 'eleven_monolingual_v1',
            voice_settings: {
              stability: 0.5,
              similarity_boost: 0.75,
              style: 0,
              use_speaker_boost: true
            }
          })
        })
      )
      
      const audio = provider['currentAudio'] as MockAudio
      expect(audio.play).toHaveBeenCalled()
      expect(URL.createObjectURL).toHaveBeenCalled()
    })
    
    it('should use custom voice when specified', async () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      const text = 'Test with custom voice'
      const voiceId = 'custom-voice-id'
      
      await provider.speak(text, { voice: voiceId })
      
      expect(fetch).toHaveBeenCalledWith(
        `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}/stream`,
        expect.any(Object)
      )
    })
    
    it('should apply volume setting', async () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      await provider.speak('Test', { volume: 0.5 })
      
      const audio = provider['currentAudio'] as MockAudio
      expect(audio.volume).toBe(0.5)
    })
    
    it('should handle empty text', async () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      await provider.speak('')
      
      expect(fetch).toHaveBeenCalled()
    })
    
    it('should handle API errors', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests'
      })
      
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      await expect(provider.speak('Test')).rejects.toThrow('ElevenLabs API error: 429')
    })
    
    it('should handle audio playback errors', async () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      // Mock play to reject
      MockAudio.prototype.play = vi.fn(() => Promise.reject(new Error('Playback failed')))
      
      await expect(provider.speak('Test')).rejects.toThrow('Playback failed')
    })
    
    it('should queue multiple speech requests', async () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      // Mock play to take longer
      let playCount = 0
      MockAudio.prototype.play = vi.fn(() => {
        playCount++
        return new Promise(resolve => {
          setTimeout(() => {
            if (provider['currentAudio']?.onended) {
              provider['currentAudio'].onended()
            }
            resolve()
          }, 50)
        })
      })
      
      // Queue multiple requests
      const promise1 = provider.speak('First')
      const promise2 = provider.speak('Second')
      const promise3 = provider.speak('Third')
      
      await Promise.all([promise1, promise2, promise3])
      
      expect(playCount).toBe(3)
      expect(fetch).toHaveBeenCalledTimes(3)
    })
    
    it('should clean up object URLs after playback', async () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      await provider.speak('Test')
      
      // Check that object URL was created
      expect(URL.createObjectURL).toHaveBeenCalled()
      const createdUrl = (URL.createObjectURL as any).mock.results[0].value
      
      // Wait for cleanup after playback
      await new Promise(resolve => setTimeout(resolve, 150))
      
      expect(URL.revokeObjectURL).toHaveBeenCalledWith(createdUrl)
    })
  })

  describe('stop', () => {
    it('should stop current audio playback', async () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      // Start speaking
      provider.speak('Long text that takes time')
      
      // Wait a bit then stop
      await new Promise(resolve => setTimeout(resolve, 10))
      provider.stop()
      
      const audio = provider['currentAudio'] as MockAudio
      expect(audio.pause).toHaveBeenCalled()
    })
    
    it('should clear speech queue', async () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      // Queue multiple speeches
      provider.speak('First')
      provider.speak('Second')
      provider.speak('Third')
      
      // Stop immediately
      provider.stop()
      
      // Only the first should have started
      expect(fetch).toHaveBeenCalledTimes(1)
    })
    
    it('should clean up resources on stop', async () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      // Start speaking
      provider.speak('Test')
      await new Promise(resolve => setTimeout(resolve, 10))
      
      // Get the created URL before stopping
      const createdUrl = (URL.createObjectURL as any).mock.results[0]?.value
      
      // Stop
      provider.stop()
      
      if (createdUrl) {
        expect(URL.revokeObjectURL).toHaveBeenCalledWith(createdUrl)
      }
    })
    
    it('should be safe to call when not playing', () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      // Should not throw
      expect(() => provider.stop()).not.toThrow()
    })
  })

  describe('edge cases', () => {
    it('should handle network errors', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(new Error('Network error'))
      
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      await expect(provider.speak('Test')).rejects.toThrow('Network error')
    })
    
    it('should handle blob creation errors', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        blob: () => Promise.reject(new Error('Blob creation failed'))
      })
      
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      await expect(provider.speak('Test')).rejects.toThrow('Blob creation failed')
    })
    
    it('should handle invalid volume values', async () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      
      // Provider doesn't clamp values, just passes them through
      await provider.speak('Test', { volume: -1 })
      let audio = provider['currentAudio'] as MockAudio
      expect(audio.volume).toBe(-1)
      
      await provider.speak('Test', { volume: 2 })
      audio = provider['currentAudio'] as MockAudio
      expect(audio.volume).toBe(2)
    })
    
    it('should handle very long text', async () => {
      const provider = new ElevenLabsTTSProvider('test-api-key')
      const longText = 'a'.repeat(5000)
      
      await provider.speak(longText)
      
      const call = (fetch as any).mock.calls[0]
      const body = JSON.parse(call[1].body)
      expect(body.text).toBe(longText)
    })
  })
})