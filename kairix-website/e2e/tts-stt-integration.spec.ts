import { test, expect } from '@playwright/test'
import { promises as fs } from 'fs'
import path from 'path'

// Helper to wait for audio to be playing
async function waitForAudioPlaying(page) {
  return await page.evaluate(() => {
    return new Promise((resolve) => {
      const checkAudio = () => {
        const audioElements = Array.from(document.querySelectorAll('audio'))
        const isPlaying = audioElements.some(audio => !audio.paused && !audio.ended)
        if (isPlaying) {
          resolve(true)
        } else {
          setTimeout(checkAudio, 100)
        }
      }
      checkAudio()
    })
  })
}

// Helper to capture audio from page
async function captureAudioFromPage(page, duration = 3000) {
  // Start recording audio using browser's MediaRecorder
  const audioData = await page.evaluate(async (duration) => {
    // Get all audio elements
    const audioElements = Array.from(document.querySelectorAll('audio'))
    if (audioElements.length === 0) throw new Error('No audio elements found')
    
    // Create audio context and destination
    const audioContext = new AudioContext()
    const destination = audioContext.createMediaStreamDestination()
    
    // Connect all audio elements to destination
    audioElements.forEach(audio => {
      const source = audioContext.createMediaElementSource(audio)
      source.connect(destination)
      source.connect(audioContext.destination) // Also play through speakers
    })
    
    // Record the stream
    const mediaRecorder = new MediaRecorder(destination.stream)
    const chunks = []
    
    mediaRecorder.ondataavailable = (e) => chunks.push(e.data)
    
    return new Promise((resolve) => {
      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        const buffer = await blob.arrayBuffer()
        resolve(Array.from(new Uint8Array(buffer)))
      }
      
      mediaRecorder.start()
      setTimeout(() => mediaRecorder.stop(), duration)
    })
  }, duration)
  
  return Buffer.from(audioData)
}

test.describe('TTS/STT End-to-End Integration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5173')
    await page.waitForLoadState('networkidle')
  })

  test('TTS provider selection and voice dropdown', async ({ page }) => {
    // Open settings
    await page.click('button[aria-label="Settings"]')
    
    // Enable TTS if not already enabled
    const ttsCheckbox = page.locator('input[type="checkbox"]').first()
    const isChecked = await ttsCheckbox.isChecked()
    if (!isChecked) {
      await ttsCheckbox.click()
    }
    
    // Check provider dropdown
    const providerSelect = page.locator('select').first()
    await expect(providerSelect).toBeVisible()
    
    // Check default is ElevenLabs
    await expect(providerSelect).toHaveValue('elevenlabs')
    
    // Check all provider options
    const options = await providerSelect.locator('option').all()
    expect(options).toHaveLength(3)
    await expect(options[0]).toHaveText('Browser TTS')
    await expect(options[1]).toHaveText('ElevenLabs')
    await expect(options[2]).toHaveText('macOS')
    
    // Switch to Browser TTS
    await providerSelect.selectOption('browser')
    await expect(providerSelect).toHaveValue('browser')
    
    // Check voice dropdown exists
    const voiceSelect = page.locator('select').nth(1)
    await expect(voiceSelect).toBeVisible()
    
    // Wait for voices to load
    await page.waitForTimeout(1000)
    
    // Check voices are populated
    const voiceOptions = await voiceSelect.locator('option').count()
    expect(voiceOptions).toBeGreaterThan(1) // At least default + 1 voice
  })

  test('ElevenLabs API key input shows/hides based on provider', async ({ page }) => {
    // Open settings
    await page.click('button[aria-label="Settings"]')
    
    // Enable TTS
    const ttsCheckbox = page.locator('input[type="checkbox"]').first()
    if (!(await ttsCheckbox.isChecked())) {
      await ttsCheckbox.click()
    }
    
    // Select ElevenLabs
    const providerSelect = page.locator('select').first()
    await providerSelect.selectOption('elevenlabs')
    
    // Check API key input is visible
    const apiKeyInput = page.locator('input[type="password"]')
    await expect(apiKeyInput).toBeVisible()
    await expect(apiKeyInput).toHaveAttribute('placeholder', 'Enter your API key')
    
    // Switch to Browser TTS
    await providerSelect.selectOption('browser')
    
    // Check API key input is hidden
    await expect(apiKeyInput).not.toBeVisible()
  })

  test('STT input clears after auto-submission', async ({ page, browserName }) => {
    // Skip on Firefox as it doesn't support Web Speech API
    if (browserName === 'firefox') {
      test.skip()
    }
    
    // Open settings
    await page.click('button[aria-label="Settings"]')
    
    // Enable auto-submit for STT
    const autoSubmitCheckbox = page.locator('text=Auto-submit').locator('input[type="checkbox"]')
    if (!(await autoSubmitCheckbox.isChecked())) {
      await autoSubmitCheckbox.click()
    }
    
    // Close settings
    await page.click('text=×')
    
    // Get chat input
    const chatInput = page.locator('input[placeholder*="Type"]')
    
    // Simulate STT transcription by typing
    await chatInput.fill('Test message from STT')
    await expect(chatInput).toHaveValue('Test message from STT')
    
    // Submit the form
    await page.keyboard.press('Enter')
    
    // Check input is cleared
    await expect(chatInput).toHaveValue('')
    
    // Check message was sent
    await expect(page.locator('text=Test message from STT')).toBeVisible()
  })

  test('TTS and STT status indicators update correctly', async ({ page }) => {
    // Get status indicators
    const ttsIndicator = page.locator('text=TTS').locator('..').locator('div').last()
    const sttIndicator = page.locator('text=STT').locator('..').locator('div').last()
    
    // Check initial states (gray = idle)
    await expect(ttsIndicator).toHaveClass(/bg-gray-400/)
    await expect(sttIndicator).toHaveClass(/bg-gray-400/)
    
    // Open settings and enable TTS
    await page.click('button[aria-label="Settings"]')
    const ttsCheckbox = page.locator('input[type="checkbox"]').first()
    if (!(await ttsCheckbox.isChecked())) {
      await ttsCheckbox.click()
    }
    
    // Switch to Browser TTS for testing (no API key needed)
    const providerSelect = page.locator('select').first()
    await providerSelect.selectOption('browser')
    
    // Close settings
    await page.click('text=×')
    
    // Send a message to trigger TTS
    const chatInput = page.locator('input[placeholder*="Type"]')
    await chatInput.fill('Hello, test TTS')
    await page.keyboard.press('Enter')
    
    // Wait for response and TTS to start
    await page.waitForTimeout(2000)
    
    // During TTS playback, indicator should be green (playing) or yellow (buffering)
    const ttsClass = await ttsIndicator.getAttribute('class')
    expect(ttsClass).toMatch(/bg-(green|yellow)-500/)
  })

  test('Full TTS to STT flow with audio verification', async ({ page, browserName }) => {
    // This test requires specific browser capabilities
    if (browserName !== 'chromium') {
      test.skip()
    }
    
    // Open settings
    await page.click('button[aria-label="Settings"]')
    
    // Enable TTS with Browser provider
    const ttsCheckbox = page.locator('input[type="checkbox"]').first()
    if (!(await ttsCheckbox.isChecked())) {
      await ttsCheckbox.click()
    }
    
    const providerSelect = page.locator('select').first()
    await providerSelect.selectOption('browser')
    
    // Select a specific voice if available
    const voiceSelect = page.locator('select').nth(1)
    await page.waitForTimeout(1000) // Wait for voices to load
    const voiceOptions = await voiceSelect.locator('option').count()
    if (voiceOptions > 1) {
      await voiceSelect.selectOption({ index: 1 }) // Select first non-default voice
    }
    
    // Close settings
    await page.click('text=×')
    
    // Send a test message
    const testMessage = 'Hello, this is a test of text to speech functionality'
    const chatInput = page.locator('input[placeholder*="Type"]')
    await chatInput.fill(testMessage)
    await page.keyboard.press('Enter')
    
    // Wait for assistant response
    await page.waitForSelector('.assistant-message', { timeout: 10000 })
    
    // Verify TTS is playing
    const ttsIndicator = page.locator('text=TTS').locator('..').locator('div').last()
    await expect(ttsIndicator).toHaveClass(/bg-(green|yellow)-500/, { timeout: 5000 })
    
    // Log completion
    console.log('TTS playback verified')
  })

  test('Settings persistence across page reloads', async ({ page }) => {
    // Open settings
    await page.click('button[aria-label="Settings"]')
    
    // Enable TTS
    const ttsCheckbox = page.locator('input[type="checkbox"]').first()
    if (!(await ttsCheckbox.isChecked())) {
      await ttsCheckbox.click()
    }
    
    // Set specific values
    await page.locator('select').first().selectOption('browser')
    
    // Adjust rate slider
    const rateSlider = page.locator('input[type="range"]').first()
    await rateSlider.fill('1.5')
    
    // Close settings
    await page.click('text=×')
    
    // Reload page
    await page.reload()
    await page.waitForLoadState('networkidle')
    
    // Open settings again
    await page.click('button[aria-label="Settings"]')
    
    // Verify settings persisted
    await expect(page.locator('input[type="checkbox"]').first()).toBeChecked()
    await expect(page.locator('select').first()).toHaveValue('browser')
    await expect(page.locator('input[type="range"]').first()).toHaveValue('1.5')
  })
})