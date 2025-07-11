import { test, expect } from '@playwright/test'
import { setupMockServer, mockMediaDevices } from './mock-server'

test.describe('Voice Flow Screenshots', () => {
  test('capture key stages of voice interaction', async ({ page }) => {
    // Set up mock server and media devices
    await setupMockServer(page)
    await mockMediaDevices(page)
    
    // Set API key in localStorage before navigating
    await page.addInitScript(() => {
      localStorage.setItem('apiKey', 'test-api-key')
    })
    
    // Navigate to the app
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // 1. Initial app load
    await page.screenshot({ path: 'e2e/screenshots/01-initial-load.png', fullPage: true })
    
    // 2. Open settings
    await page.click('button[aria-label="Settings"]')
    await page.waitForTimeout(500) // Wait for animation
    await page.screenshot({ path: 'e2e/screenshots/02-settings-open.png', fullPage: true })
    
    // 3. Close settings
    await page.click('button[aria-label="Close settings"]')
    await page.waitForTimeout(500)
    await page.screenshot({ path: 'e2e/screenshots/03-main-chat.png', fullPage: true })
    
    // 4. Type a message
    await page.fill('textarea[placeholder="Type a message..."]', 'Hello, AI assistant!')
    await page.screenshot({ path: 'e2e/screenshots/04-message-typed.png', fullPage: true })
    
    // 5. Send message and get response
    await page.click('button[aria-label="Send message"]')
    await page.waitForSelector('text=Hello from the mock server!')
    await page.screenshot({ path: 'e2e/screenshots/05-conversation.png', fullPage: true })
    
    // 6. Push-to-talk button hover
    const micButton = page.locator('button[aria-label="Push to talk"]')
    await micButton.hover()
    await page.screenshot({ path: 'e2e/screenshots/06-mic-button-hover.png', fullPage: true })
    
    // 7. Recording state (simulated)
    await page.evaluate(() => {
      // Simulate STT overlay
      const overlay = document.createElement('div')
      overlay.setAttribute('data-testid', 'stt-overlay')
      overlay.style.cssText = 'position: fixed; inset: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 9999;'
      overlay.innerHTML = `
        <div style="text-align: center; color: white;">
          <div style="width: 120px; height: 120px; border-radius: 50%; background: red; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center;">
            <svg width="60" height="60" viewBox="0 0 24 24" fill="white">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
          </div>
          <h2 style="font-size: 24px; margin: 0;">Listening...</h2>
          <div data-testid="volume-indicator" style="margin-top: 20px;">
            <div style="display: flex; gap: 4px; justify-content: center;">
              ${[1,2,3,4].map(i => `<div style="width: 8px; height: ${20 + i * 10}px; background: white; animation: pulse 0.5s infinite;"></div>`).join('')}
            </div>
          </div>
        </div>
      `
      document.body.appendChild(overlay)
    })
    await page.waitForTimeout(500)
    await page.screenshot({ path: 'e2e/screenshots/07-recording-active.png', fullPage: true })
    
    // 8. Remove overlay and show transcription
    await page.evaluate(() => {
      const overlay = document.querySelector('[data-testid="stt-overlay"]')
      if (overlay) overlay.remove()
      const textarea = document.querySelector('textarea[placeholder="Type a message..."]') as HTMLTextAreaElement
      if (textarea) {
        textarea.value = 'This is my transcribed voice message'
        textarea.dispatchEvent(new Event('input', { bubbles: true }))
      }
    })
    await page.waitForTimeout(500)
    await page.screenshot({ path: 'e2e/screenshots/08-transcription-complete.png', fullPage: true })
    
    // 9. Activity status bars
    await page.evaluate(() => {
      // Simulate different TTS/STT states
      window.dispatchEvent(new CustomEvent('tts-state-change', { detail: { state: 'playing' } }))
      window.dispatchEvent(new CustomEvent('stt-state-change', { detail: { state: 'listening' } }))
    })
    await page.waitForTimeout(500)
    await page.screenshot({ path: 'e2e/screenshots/09-activity-status.png', fullPage: true })
    
    // 10. Error state
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('stt-state-change', { 
        detail: { state: 'error', error: 'Microphone access denied' } 
      }))
    })
    await page.waitForTimeout(500)
    await page.screenshot({ path: 'e2e/screenshots/10-error-state.png', fullPage: true })
  })
})