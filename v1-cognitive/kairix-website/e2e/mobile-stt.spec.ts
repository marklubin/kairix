import { test, expect, Page } from '@playwright/test';

// Test on mobile viewports and devices
test.describe('Mobile STT Functionality', () => {
  test.use({ 
    viewport: { width: 375, height: 667 }, // iPhone SE size
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
  });

  let mockRecognition: any;

  test.beforeEach(async ({ page }) => {
    // Mock speech recognition API
    await page.addInitScript(() => {
      const mockRecognition = {
        continuous: false,
        interimResults: true,
        lang: 'en-US',
        maxAlternatives: 1,
        start: () => {
          console.log('Mock recognition started');
          mockRecognition.onstart?.();
        },
        stop: () => {
          console.log('Mock recognition stopped');
          mockRecognition.onend?.();
        },
        abort: () => {
          console.log('Mock recognition aborted');
          mockRecognition.onend?.();
        },
        onstart: null,
        onresult: null,
        onerror: null,
        onend: null,
        onaudiostart: null,
        onsoundstart: null,
        onspeechstart: null,
      };

      (window as any).SpeechRecognition = function() {
        return mockRecognition;
      };
      (window as any).webkitSpeechRecognition = (window as any).SpeechRecognition;
      (window as any).__mockRecognition = mockRecognition;
    });

    await page.goto('/');
  });

  test('should show interim results while speaking on mobile', async ({ page }) => {
    // Click mic button
    await page.getByTestId('chat-mic-button').click();

    // Wait for STT overlay to appear
    await expect(page.getByText('Listening...')).toBeVisible();

    // Simulate interim speech results
    await page.evaluate(() => {
      const mockRec = (window as any).__mockRecognition;
      
      // First interim result
      mockRec.onresult?.({
        results: [{
          0: { transcript: 'Hello' },
          isFinal: false
        }]
      });
    });

    // Should show interim text immediately
    await expect(page.getByText('Hello')).toBeVisible();

    // Add more interim results
    await page.evaluate(() => {
      const mockRec = (window as any).__mockRecognition;
      
      // Accumulated interim results
      mockRec.onresult?.({
        results: [
          { 0: { transcript: 'Hello' }, isFinal: false },
          { 0: { transcript: 'world' }, isFinal: false }
        ]
      });
    });

    // Should show accumulated text
    await expect(page.getByText('Hello world')).toBeVisible();

    // Final result
    await page.evaluate(() => {
      const mockRec = (window as any).__mockRecognition;
      
      mockRec.onresult?.({
        results: [
          { 0: { transcript: 'Hello' }, isFinal: false },
          { 0: { transcript: 'world' }, isFinal: true }
        ]
      });
    });

    // Click stop button
    await page.getByRole('button', { name: /stop/i }).click();

    // Should auto-submit the text
    await expect(page.getByText('Hello world').first()).toBeVisible();
  });

  test('should handle touch events without double-triggering', async ({ page }) => {
    let startCount = 0;
    
    // Track recognition starts
    await page.exposeFunction('trackStart', () => {
      startCount++;
    });

    await page.evaluate(() => {
      const mockRec = (window as any).__mockRecognition;
      const originalStart = mockRec.start;
      mockRec.start = () => {
        (window as any).trackStart();
        originalStart.call(mockRec);
      };
    });

    // Simulate rapid touches on mic button
    const micButton = page.getByTestId('chat-mic-button');
    
    // First touch
    await micButton.click();
    await page.waitForTimeout(50);
    
    // Try rapid second touch - should be ignored
    await micButton.click({ force: true });
    
    // Wait for debounce
    await page.waitForTimeout(400);
    
    // Should only have started once
    expect(startCount).toBe(1);
  });

  test('should handle mobile browser no-speech gracefully', async ({ page }) => {
    await page.getByTestId('chat-mic-button').click();
    
    // Simulate no-speech error (common on mobile)
    await page.evaluate(() => {
      const mockRec = (window as any).__mockRecognition;
      mockRec.onerror?.({ error: 'no-speech' });
    });

    // Should close overlay without error
    await expect(page.getByText('Listening...')).not.toBeVisible();
    
    // Mic button should be enabled again
    await expect(page.getByTestId('chat-mic-button')).toBeEnabled();
  });

  test('should not use continuous mode on mobile', async ({ page }) => {
    await page.getByTestId('chat-mic-button').click();

    // Check that continuous mode is disabled
    const isContinuous = await page.evaluate(() => {
      return (window as any).__mockRecognition.continuous;
    });

    expect(isContinuous).toBe(false);
  });

  test('should handle permission denial on mobile', async ({ page }) => {
    // Override getUserMedia to simulate permission denial
    await page.evaluate(() => {
      navigator.mediaDevices.getUserMedia = () => 
        Promise.reject(new DOMException('Permission denied', 'NotAllowedError'));
    });

    await page.getByTestId('chat-mic-button').click();

    // Should show permission error
    await expect(page.locator('text=/Microphone permission denied/i')).toBeVisible();
  });
});

// Test on actual mobile devices using Chrome DevTools Protocol
test.describe('Mobile STT on Real Devices', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'Chrome DevTools Protocol only');

  test('should work on emulated iPhone', async ({ browser }) => {
    const context = await browser.newContext({
      ...test.use,
      viewport: { width: 390, height: 844 }, // iPhone 12 Pro
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15',
      hasTouch: true,
      isMobile: true,
    });

    const page = await context.newPage();
    
    // Enable touch events
    const cdpSession = await context.newCDPSession(page);
    await cdpSession.send('Emulation.setTouchEmulationEnabled', { enabled: true });

    await page.goto('/');

    // Test touch on mic button
    const micButton = page.getByTestId('chat-mic-button');
    await micButton.tap();

    // Should not have any visual glitches or vibrations
    // (Can't directly test for vibration, but ensuring smooth interaction)
    await expect(page.getByText('Listening...')).toBeVisible({ timeout: 1000 });
  });
});