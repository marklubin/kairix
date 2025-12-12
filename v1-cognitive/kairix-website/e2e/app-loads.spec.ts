import { test, expect } from '@playwright/test'

test('app loads successfully', async ({ page }) => {
  // Navigate to the app
  await page.goto('/')
  
  // Check for console errors
  const consoleErrors: string[] = []
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text())
    }
  })
  
  // Wait for the app to fully load
  await page.waitForLoadState('networkidle')
  
  // The app should show either the auth screen or the main app
  const authInput = page.locator('input[placeholder="Enter access key"]')
  const mainApp = page.locator('textarea[placeholder="Type a message..."]')
  
  // Either auth screen or main app should be visible
  const authVisible = await authInput.isVisible().catch(() => false)
  const mainVisible = await mainApp.isVisible().catch(() => false)
  
  expect(authVisible || mainVisible).toBe(true)
  
  // Check for no console errors
  expect(consoleErrors).toEqual([])
  
  // Check page title
  await expect(page).toHaveTitle('Vite + React + TS')
  
  // Take a screenshot for verification
  await page.screenshot({ path: 'e2e/screenshots/app-loaded.png' })
})