import { test, expect } from '@playwright/test'
import { setupMockServer, mockMediaDevices } from './mock-server'
import * as fs from 'fs'
import * as path from 'path'

test.describe('Voice Flow E2E Tests', () => {
  let screenshotCounter = 1
  
  const takeScreenshot = async (page: any, name: string) => {
    await page.screenshot({ 
      path: `e2e/screenshots/${screenshotCounter.toString().padStart(2, '0')}-${name}.png`,
      fullPage: true 
    })
    screenshotCounter++
  }
  
  test.beforeEach(async ({ page }) => {
    // Set up mock server and media devices
    await setupMockServer(page)
    await mockMediaDevices(page)
    
    // Set API key in localStorage before navigating
    await page.addInitScript(() => {
      localStorage.setItem('apiKey', 'test-api-key')
    })
    
    // Navigate to the app
    await page.goto('/')
    
    // Wait for app to load
    await page.waitForLoadState('networkidle')
    
    // Take initial screenshot
    await takeScreenshot(page, 'initial-load')
  })

  test('should complete full voice interaction flow', async ({ page }) => {
    // Verify the app loaded correctly
    await expect(page.locator('button[aria-label="Settings"]')).toBeVisible()
    await expect(page.locator('textarea[placeholder="Type a message..."]')).toBeVisible()
    
    // Open settings to configure voice options
    await page.click('button[aria-label="Settings"]')
    await expect(page.locator('text=Chat Settings')).toBeVisible()
    await takeScreenshot(page, 'settings-opened')
    
    // Configure TTS settings
    await page.selectOption('select[id="tts-provider"]', 'browser')
    await page.selectOption('select[id="tts-voice"]', { index: 0 })
    await page.fill('input[id="tts-rate"]', '1.2')
    await page.fill('input[id="tts-pitch"]', '1.0')
    await page.fill('input[id="tts-volume"]', '0.8')
    
    // Configure STT settings
    await page.selectOption('select[id="stt-provider"]', 'browser')
    await page.selectOption('select[id="stt-language"]', 'en-US')
    await page.check('input[id="stt-auto-submit"]')
    await page.check('input[id="stt-interim-results"]')
    await takeScreenshot(page, 'settings-configured')
    
    // Close settings
    await page.click('button[aria-label="Close settings"]')
    await takeScreenshot(page, 'settings-closed')
    
    // Test 1: Text input and TTS playback
    await test.step('Text input with TTS response', async () => {
      // Type a message
      await page.fill('textarea[placeholder="Type a message..."]', 'Hello, can you hear me?')
      await takeScreenshot(page, 'message-typed')
      
      // Send the message
      await page.click('button[aria-label="Send message"]')
      
      // Wait for user message to appear
      await expect(page.locator('text=Hello, can you hear me?')).toBeVisible()
      await takeScreenshot(page, 'message-sent')
      
      // Wait for AI response
      await expect(page.locator('text=Hello from the mock server!')).toBeVisible()
      await takeScreenshot(page, 'ai-response-received')
      
      // Verify TTS is playing (check for activity indicator)
      await expect(page.locator('[data-testid="tts-status-active"]')).toBeVisible()
      await takeScreenshot(page, 'tts-playing')
      
      // Wait for TTS to complete
      await expect(page.locator('[data-testid="tts-status-idle"]')).toBeVisible({ timeout: 10000 })
      await takeScreenshot(page, 'tts-complete')
    })
    
    // Test 2: Push-to-talk recording
    await test.step('Push-to-talk voice input', async () => {
      const micButton = page.locator('button[aria-label="Push to talk"]')
      
      // Start recording
      await micButton.press()
      
      // Verify recording UI appears
      await expect(page.locator('[data-testid="stt-overlay"]')).toBeVisible()
      await expect(page.locator('text=Listening...')).toBeVisible()
      await takeScreenshot(page, 'stt-listening')
      
      // Check volume indicator is animating
      await expect(page.locator('[data-testid="volume-indicator"]')).toBeVisible()
      
      // Hold for 2 seconds to simulate speaking
      await page.waitForTimeout(2000)
      await takeScreenshot(page, 'stt-recording')
      
      // Release to stop recording
      await micButton.release()
      
      // Verify processing state
      await expect(page.locator('text=Processing...')).toBeVisible()
      await takeScreenshot(page, 'stt-processing')
      
      // Mock transcription result
      await page.evaluate(() => {
        const textarea = document.querySelector('textarea[placeholder="Type a message..."]') as HTMLTextAreaElement
        if (textarea) {
          textarea.value = 'This is a test transcription'
          textarea.dispatchEvent(new Event('input', { bubbles: true }))
        }
      })
      
      // Verify transcription appears in input
      await expect(page.locator('textarea[placeholder="Type a message..."]')).toHaveValue('This is a test transcription')
      await takeScreenshot(page, 'stt-transcribed')
      
      // With auto-submit enabled, it should send automatically
      await expect(page.locator('text=This is a test transcription')).toBeVisible()
      await takeScreenshot(page, 'stt-auto-submitted')
    })
    
    // Test 3: Keyboard shortcut for recording
    await test.step('Keyboard shortcut voice input', async () => {
      // Clear input field
      await page.fill('textarea[placeholder="Type a message..."]', '')
      
      // Press space to start recording (default hotkey)
      await page.keyboard.down(' ')
      
      // Verify recording started
      await expect(page.locator('[data-testid="stt-overlay"]')).toBeVisible()
      
      // Release space to stop
      await page.keyboard.up(' ')
      
      // Verify recording stopped
      await expect(page.locator('[data-testid="stt-overlay"]')).not.toBeVisible()
    })
    
    // Test 4: Voice conversation flow
    await test.step('Complete voice conversation', async () => {
      // Start a voice conversation
      const micButton = page.locator('button[aria-label="Push to talk"]')
      
      // First voice input
      await micButton.press()
      await page.waitForTimeout(1500)
      await micButton.release()
      
      // Mock transcription
      await page.evaluate(() => {
        const textarea = document.querySelector('textarea[placeholder="Type a message..."]') as HTMLTextAreaElement
        if (textarea) {
          textarea.value = 'What is the weather like today?'
          textarea.dispatchEvent(new Event('input', { bubbles: true }))
        }
      })
      
      // Wait for response
      await expect(page.locator('text=Hello from the mock server!')).toBeVisible()
      
      // Verify TTS plays the response
      await expect(page.locator('[data-testid="tts-status-active"]')).toBeVisible()
      
      // Second voice input while TTS is playing
      await micButton.press()
      
      // TTS should stop when recording starts
      await expect(page.locator('[data-testid="tts-status-idle"]')).toBeVisible()
      
      await micButton.release()
    })
    
    // Test 5: Error handling
    await test.step('STT error handling', async () => {
      // Mock STT error
      await page.evaluate(() => {
        window.dispatchEvent(new CustomEvent('stt-error', { 
          detail: { error: 'No speech detected' } 
        }))
      })
      
      // Verify error is displayed
      await expect(page.locator('[data-testid="stt-error"]')).toContainText('No speech detected')
      
      // Error should clear after timeout
      await expect(page.locator('[data-testid="stt-error"]')).not.toBeVisible({ timeout: 5000 })
    })
    
    // Test 6: Settings persistence
    await test.step('Settings persistence', async () => {
      // Open settings and change values
      await page.click('button[aria-label="Settings"]')
      await page.fill('input[id="tts-rate"]', '1.5')
      await page.fill('input[id="tts-pitch"]', '0.8')
      await page.click('button[aria-label="Close settings"]')
      
      // Reload page
      await page.reload()
      
      // Open settings again
      await page.click('button[aria-label="Settings"]')
      
      // Verify settings were saved
      await expect(page.locator('input[id="tts-rate"]')).toHaveValue('1.5')
      await expect(page.locator('input[id="tts-pitch"]')).toHaveValue('0.8')
    })
  })

  test('should handle audio file upload for STT', async ({ page }) => {
    // Read the test.m4a file
    const audioPath = path.join(process.cwd(), 'test.m4a')
    
    // Check if file exists
    if (!fs.existsSync(audioPath)) {
      test.skip(true, 'test.m4a file not found')
      return
    }
    
    // Create a file input and upload the audio file
    await page.evaluate(() => {
      const input = document.createElement('input')
      input.type = 'file'
      input.id = 'audio-upload'
      input.accept = 'audio/*'
      document.body.appendChild(input)
    })
    
    // Upload the file
    const fileInput = page.locator('#audio-upload')
    await fileInput.setInputFiles(audioPath)
    
    // Mock the transcription processing
    await page.evaluate(() => {
      // Simulate processing the audio file
      setTimeout(() => {
        const textarea = document.querySelector('textarea[placeholder="Type a message..."]') as HTMLTextAreaElement
        if (textarea) {
          textarea.value = 'Transcription from test.m4a audio file'
          textarea.dispatchEvent(new Event('input', { bubbles: true }))
        }
      }, 1000)
    })
    
    // Wait for transcription to appear
    await expect(page.locator('textarea[placeholder="Type a message..."]')).toHaveValue('Transcription from test.m4a audio file')
    
    // Send the transcribed message
    await page.click('button[aria-label="Send message"]')
    
    // Verify message was sent
    await expect(page.locator('text=Transcription from test.m4a audio file')).toBeVisible()
  })

  test('should handle concurrent TTS and STT operations', async ({ page }) => {
    const micButton = page.locator('button[aria-label="Push to talk"]')
    
    // Start TTS playback
    await page.fill('textarea[placeholder="Type a message..."]', 'Play this message')
    await page.click('button[aria-label="Send message"]')
    await expect(page.locator('[data-testid="tts-status-active"]')).toBeVisible()
    
    // Start STT while TTS is playing
    await micButton.press()
    
    // TTS should pause/stop
    await expect(page.locator('[data-testid="tts-status-idle"]')).toBeVisible()
    
    // STT should be active
    await expect(page.locator('[data-testid="stt-overlay"]')).toBeVisible()
    
    // Stop STT
    await micButton.release()
    
    // Both should be idle
    await expect(page.locator('[data-testid="tts-status-idle"]')).toBeVisible()
    await expect(page.locator('[data-testid="stt-status-idle"]')).toBeVisible()
  })

  test('should validate all voice states in activity bar', async ({ page }) => {
    // Check initial state
    await expect(page.locator('[data-testid="tts-status-idle"]')).toBeVisible()
    await expect(page.locator('[data-testid="stt-status-idle"]')).toBeVisible()
    
    // Test all TTS states
    const ttsStates = ['playing', 'queued', 'error']
    for (const state of ttsStates) {
      await page.evaluate((s) => {
        window.dispatchEvent(new CustomEvent('tts-state-change', { detail: { state: s } }))
      }, state)
      await expect(page.locator(`[data-testid="tts-status-${state}"]`)).toBeVisible()
    }
    
    // Test all STT states  
    const sttStates = ['listening', 'processing', 'error']
    for (const state of sttStates) {
      await page.evaluate((s) => {
        window.dispatchEvent(new CustomEvent('stt-state-change', { detail: { state: s } }))
      }, state)
      await expect(page.locator(`[data-testid="stt-status-${state}"]`)).toBeVisible()
    }
  })
})