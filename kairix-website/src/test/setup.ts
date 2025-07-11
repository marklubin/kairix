import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// Set environment variables for tests
process.env.VITE_API_URL = 'http://localhost:8888'
process.env.VITE_KAIRIX_WEBSITE_PORT = '5173'

// Mock import.meta.env for Vite
vi.stubGlobal('import.meta.env', {
  VITE_API_URL: 'http://localhost:8888',
  VITE_KAIRIX_WEBSITE_PORT: '5173'
})

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock HTMLMediaElement
window.HTMLMediaElement.prototype.play = vi.fn(() => Promise.resolve())
window.HTMLMediaElement.prototype.pause = vi.fn()
window.HTMLMediaElement.prototype.load = vi.fn()

// Mock MediaRecorder
class MockMediaRecorder {
  state = 'inactive'
  ondataavailable: ((event: any) => void) | null = null
  onstop: (() => void) | null = null
  onerror: ((event: any) => void) | null = null
  onstart: (() => void) | null = null

  constructor(public stream: MediaStream, public options?: MediaRecorderOptions) {}

  start() {
    this.state = 'recording'
    if (this.onstart) this.onstart()
  }

  stop() {
    this.state = 'inactive'
    if (this.onstop) this.onstop()
  }

  pause() {
    this.state = 'paused'
  }

  resume() {
    this.state = 'recording'
  }

  static isTypeSupported(mimeType: string) {
    return mimeType === 'audio/webm' || mimeType === 'audio/mp4'
  }
}

// @ts-ignore
window.MediaRecorder = MockMediaRecorder

// Mock MediaStream
class MockMediaStream {
  constructor() {
    // MediaStream mock implementation
  }
}

// @ts-ignore
window.MediaStream = MockMediaStream

// Mock navigator.mediaDevices
Object.defineProperty(navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: vi.fn().mockImplementation(() => 
      Promise.resolve(new MockMediaStream())
    ),
    enumerateDevices: vi.fn().mockImplementation(() =>
      Promise.resolve([
        {
          deviceId: 'default',
          kind: 'audioinput',
          label: 'Default Microphone',
          groupId: 'default-group'
        }
      ])
    )
  }
})

// Mock Web Audio API
class MockAudioContext {
  createMediaStreamSource = vi.fn()
  createAnalyser = vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    fftSize: 2048,
    getByteTimeDomainData: vi.fn()
  }))
  close = vi.fn()
}

// @ts-expect-error
window.AudioContext = MockAudioContext
// @ts-expect-error
window.webkitAudioContext = MockAudioContext

// Mock SpeechRecognition
class MockSpeechRecognition {
  continuous = false
  interimResults = false
  lang = 'en-US'
  maxAlternatives = 1
  onaudiostart = null
  onaudioend = null
  onend = null
  onerror = null
  onnomatch = null
  onresult = null
  onsoundstart = null
  onsoundend = null
  onspeechend = null
  onspeechstart = null
  onstart = null
  
  start = vi.fn()
  stop = vi.fn()
  abort = vi.fn()
  
  addEventListener = vi.fn()
  removeEventListener = vi.fn()
  dispatchEvent = vi.fn()
}

// @ts-expect-error
window.SpeechRecognition = MockSpeechRecognition
// @ts-expect-error
window.webkitSpeechRecognition = MockSpeechRecognition

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn()