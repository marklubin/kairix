import { Page } from '@playwright/test'

export async function setupMockServer(page: Page) {
  // Mock the Kairix backend API
  await page.route('**/api/chat/completions', async (route) => {
    const request = route.request()
    const postData = request.postDataJSON()
    
    // Simulate streaming response
    const encoder = new TextEncoder()
    const messages = [
      'data: {"id":"1","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}\n\n',
      'data: {"id":"1","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4","choices":[{"index":0,"delta":{"content":" from"},"finish_reason":null}]}\n\n',
      'data: {"id":"1","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4","choices":[{"index":0,"delta":{"content":" the"},"finish_reason":null}]}\n\n',
      'data: {"id":"1","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4","choices":[{"index":0,"delta":{"content":" mock"},"finish_reason":null}]}\n\n',
      'data: {"id":"1","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4","choices":[{"index":0,"delta":{"content":" server!"},"finish_reason":null}]}\n\n',
      'data: {"id":"1","object":"chat.completion.chunk","created":1234567890,"model":"gpt-4","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n',
      'data: [DONE]\n\n'
    ]
    
    const body = messages.map(msg => encoder.encode(msg))
    const stream = new ReadableStream({
      async start(controller) {
        for (const chunk of body) {
          controller.enqueue(chunk)
          await new Promise(resolve => setTimeout(resolve, 50))
        }
        controller.close()
      }
    })
    
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      headers: {
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
      body: stream
    })
  })
  
  // Mock any other API endpoints as needed
  await page.route('**/api/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok' })
    })
  })
}

export async function mockMediaDevices(page: Page) {
  await page.addInitScript(() => {
    // Mock getUserMedia for microphone access
    navigator.mediaDevices.getUserMedia = async (constraints) => {
      // Create a mock MediaStream
      const AudioContext = window.AudioContext || (window as any).webkitAudioContext
      const audioContext = new AudioContext()
      const oscillator = audioContext.createOscillator()
      const dst = audioContext.createMediaStreamDestination()
      oscillator.connect(dst)
      oscillator.start()
      return dst.stream
    }
  })
}