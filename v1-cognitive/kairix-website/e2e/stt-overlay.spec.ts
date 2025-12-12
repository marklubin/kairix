import { test, expect } from '@playwright/test';

test.describe('STT Overlay E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Start the mock server if needed
    await page.goto('http://localhost:9000');
    
    // Wait for app to load
    await page.waitForSelector('[data-testid="chat-input"]', { timeout: 5000 });
  });

  test('should show overlay when STT is activated', async ({ page }) => {
    // Press the STT hotkey
    await page.keyboard.press('Control+Shift+S');
    
    // Check overlay appears
    await expect(page.locator('.fixed.inset-0.z-50')).toBeVisible();
    await expect(page.locator('text=Listening...')).toBeVisible();
    await expect(page.locator('text=Tap to stop and send')).toBeVisible();
  });

  test('should display transcript in overlay', async ({ page }) => {
    // Mock the speech recognition API
    await page.evaluateOnNewDocument(() => {
      let recognitionInstance: any;
      
      window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      
      class MockSpeechRecognition {
        continuous = false;
        interimResults = false;
        lang = 'en-US';
        onstart: any = null;
        onresult: any = null;
        onend: any = null;
        onerror: any = null;
        
        start() {
          recognitionInstance = this;
          setTimeout(() => {
            if (this.onstart) this.onstart();
            
            // Simulate interim result
            setTimeout(() => {
              if (this.onresult) {
                this.onresult({
                  results: [{
                    0: { transcript: 'Hello world test message' },
                    isFinal: false
                  }],
                  resultIndex: 0
                });
              }
            }, 100);
          }, 50);
        }
        
        stop() {
          setTimeout(() => {
            if (this.onresult) {
              this.onresult({
                results: [{
                  0: { transcript: 'Hello world test message' },
                  isFinal: true
                }],
                resultIndex: 0
              });
            }
            if (this.onend) this.onend();
          }, 50);
        }
        
        abort() {
          if (this.onend) this.onend();
        }
      }
      
      window.SpeechRecognition = MockSpeechRecognition as any;
    });
    
    await page.reload();
    await page.waitForSelector('[data-testid="chat-input"]');
    
    // Start STT
    await page.keyboard.press('Control+Shift+S');
    
    // Wait for transcript to appear
    await expect(page.locator('text=Hello world test message')).toBeVisible({ timeout: 5000 });
  });

  test('should submit message when stop button is clicked', async ({ page }) => {
    // Mock the speech recognition API
    await page.evaluateOnNewDocument(() => {
      window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      
      class MockSpeechRecognition {
        continuous = false;
        interimResults = false;
        lang = 'en-US';
        onstart: any = null;
        onresult: any = null;
        onend: any = null;
        onerror: any = null;
        
        start() {
          setTimeout(() => {
            if (this.onstart) this.onstart();
            
            // Immediate result
            if (this.onresult) {
              this.onresult({
                results: [{
                  0: { transcript: 'Test submission message' },
                  isFinal: false
                }],
                resultIndex: 0
              });
            }
          }, 50);
        }
        
        stop() {
          setTimeout(() => {
            if (this.onresult) {
              this.onresult({
                results: [{
                  0: { transcript: 'Test submission message' },
                  isFinal: true
                }],
                resultIndex: 0
              });
            }
            if (this.onend) this.onend();
          }, 50);
        }
        
        abort() {
          if (this.onend) this.onend();
        }
      }
      
      window.SpeechRecognition = MockSpeechRecognition as any;
    });
    
    // Mock the API response
    await page.route('**/api/chat', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: 'data: {"choices":[{"delta":{"content":"Response to your message"}}]}\n\ndata: [DONE]\n\n'
      });
    });
    
    await page.reload();
    await page.waitForSelector('[data-testid="chat-input"]');
    
    // Start STT
    await page.keyboard.press('Control+Shift+S');
    
    // Wait for overlay
    await expect(page.locator('.fixed.inset-0.z-50')).toBeVisible();
    
    // Click stop button
    const stopButton = page.locator('button:has(svg)').filter({ hasText: /stop|send/i });
    await stopButton.click();
    
    // Check that message was sent
    await expect(page.locator('text=Test submission message')).toBeVisible({ timeout: 5000 });
    
    // Check that overlay is gone
    await expect(page.locator('.fixed.inset-0.z-50')).not.toBeVisible();
    
    // Check that input is cleared
    const input = page.locator('[data-testid="chat-input"]');
    await expect(input).toHaveValue('');
  });

  test('should only submit once on multiple clicks', async ({ page }) => {
    let submitCount = 0;
    
    // Mock the API to count submissions
    await page.route('**/api/chat', async route => {
      submitCount++;
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: 'data: {"choices":[{"delta":{"content":"Response"}}]}\n\ndata: [DONE]\n\n'
      });
    });
    
    // Mock speech recognition
    await page.evaluateOnNewDocument(() => {
      window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      
      class MockSpeechRecognition {
        continuous = false;
        interimResults = false;
        lang = 'en-US';
        onstart: any = null;
        onresult: any = null;
        onend: any = null;
        onerror: any = null;
        
        start() {
          setTimeout(() => {
            if (this.onstart) this.onstart();
            if (this.onresult) {
              this.onresult({
                results: [{
                  0: { transcript: 'Single submission test' },
                  isFinal: false
                }],
                resultIndex: 0
              });
            }
          }, 50);
        }
        
        stop() {
          setTimeout(() => {
            if (this.onresult) {
              this.onresult({
                results: [{
                  0: { transcript: 'Single submission test' },
                  isFinal: true
                }],
                resultIndex: 0
              });
            }
            if (this.onend) this.onend();
          }, 50);
        }
        
        abort() {
          if (this.onend) this.onend();
        }
      }
      
      window.SpeechRecognition = MockSpeechRecognition as any;
    });
    
    await page.reload();
    await page.waitForSelector('[data-testid="chat-input"]');
    
    // Start STT
    await page.keyboard.press('Control+Shift+S');
    await expect(page.locator('.fixed.inset-0.z-50')).toBeVisible();
    
    // Click stop button multiple times rapidly
    const stopButton = page.locator('button:has(svg)').filter({ hasText: /stop|send/i });
    await stopButton.click();
    await stopButton.click({ force: true });
    await stopButton.click({ force: true });
    
    // Wait for submission
    await page.waitForTimeout(1000);
    
    // Should only submit once
    expect(submitCount).toBe(1);
  });

  test('should handle errors gracefully', async ({ page }) => {
    // Mock speech recognition to fail
    await page.evaluateOnNewDocument(() => {
      window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      
      class MockSpeechRecognition {
        start() {
          setTimeout(() => {
            if (this.onerror) {
              this.onerror({ error: 'not-allowed', message: 'Microphone access denied' });
            }
          }, 50);
        }
        
        stop() {}
        abort() {}
        
        continuous = false;
        interimResults = false;
        lang = 'en-US';
        onstart: any = null;
        onresult: any = null;
        onend: any = null;
        onerror: any = null;
      }
      
      window.SpeechRecognition = MockSpeechRecognition as any;
    });
    
    await page.reload();
    await page.waitForSelector('[data-testid="chat-input"]');
    
    // Intercept alerts
    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('Microphone permission denied');
      await dialog.accept();
    });
    
    // Try to start STT
    await page.keyboard.press('Control+Shift+S');
    
    // Overlay should not appear
    await expect(page.locator('.fixed.inset-0.z-50')).not.toBeVisible({ timeout: 2000 });
  });
});