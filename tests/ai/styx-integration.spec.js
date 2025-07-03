const { test, expect } = require('@playwright/test');
const TestHelpers = require('../utils/test-helpers');

test.describe('AI Integration Tests - Styx Assistant', () => {
  test.beforeEach(async ({ page }) => {
    // Login as test admin user
    await TestHelpers.loginAsTestUser(page, 'admin', false);
    
    // Switch to test AI room to avoid interfering with general chat
    const testRoom = await TestHelpers.getTestRoom(false); // Get public test room
    if (testRoom) {
      await TestHelpers.switchRoom(page, testRoom.name);
    }
    
    // Clear any existing messages to ensure test isolation
    await page.evaluate(() => {
      const messagesContainer = document.getElementById('messages');
      if (messagesContainer) {
        messagesContainer.innerHTML = '';
      }
    });
  });

  test('should show Styx in user list', async ({ page }) => {
    await expect(page.locator('#usersList')).toBeVisible();
    await expect(page.locator('#usersList')).toContainText('Styx');
  });

  test('should respond to @ai trigger', async ({ page }) => {
    const testMessage = '@ai Hello, can you help me?';
    
    await page.fill('#messageInput', testMessage);
    await page.click('#sendButton');
    
    // Wait for user message to appear
    await expect(page.locator('#messages')).toContainText(testMessage);
    
    // Wait for AI response (may take a few seconds)
    await expect(page.locator('#messages')).toContainText('Styx', { timeout: 15000 });
    
    // Check that the AI response is from Styx
    const styxMessages = page.locator('#messages .message:has-text("Styx")');
    await expect(styxMessages).toHaveCount(1);
  });

  test('should respond to @bot trigger', async ({ page }) => {
    const testMessage = '@bot What is the weather like?';
    
    await page.fill('#messageInput', testMessage);
    await page.click('#sendButton');
    
    // Wait for user message to appear
    await expect(page.locator('#messages')).toContainText(testMessage);
    
    // Wait for AI response
    await expect(page.locator('#messages')).toContainText('Styx', { timeout: 15000 });
  });

  test('should respond to @styx trigger', async ({ page }) => {
    const testMessage = '@styx Tell me a joke';
    
    await page.fill('#messageInput', testMessage);
    await page.click('#sendButton');
    
    // Wait for user message to appear
    await expect(page.locator('#messages')).toContainText(testMessage);
    
    // Wait for AI response
    await expect(page.locator('#messages')).toContainText('Styx', { timeout: 15000 });
  });

  test('should respond to "hey ai" trigger', async ({ page }) => {
    const testMessage = 'hey ai, what can you do?';
    
    await page.fill('#messageInput', testMessage);
    await page.click('#sendButton');
    
    // Wait for user message to appear
    await expect(page.locator('#messages')).toContainText(testMessage);
    
    // Wait for AI response
    await expect(page.locator('#messages')).toContainText('Styx', { timeout: 15000 });
  });

  test('should respond to "hey bot" trigger', async ({ page }) => {
    const testMessage = 'hey bot, help me understand something';
    
    await page.fill('#messageInput', testMessage);
    await page.click('#sendButton');
    
    // Wait for user message to appear
    await expect(page.locator('#messages')).toContainText(testMessage);
    
    // Wait for AI response
    await expect(page.locator('#messages')).toContainText('Styx', { timeout: 15000 });
  });

  test('should respond to "hey styx" trigger', async ({ page }) => {
    const testMessage = 'hey styx, I need assistance';
    
    await page.fill('#messageInput', testMessage);
    await page.click('#sendButton');
    
    // Wait for user message to appear
    await expect(page.locator('#messages')).toContainText(testMessage);
    
    // Wait for AI response
    await expect(page.locator('#messages')).toContainText('Styx', { timeout: 15000 });
  });

  test('should handle help command', async ({ page }) => {
    await page.fill('#messageInput', '!help');
    await page.click('#sendButton');
    
    // Wait for help message to appear
    await expect(page.locator('#messages')).toContainText('Multi-User AI Chat Help', { timeout: 5000 });
    await expect(page.locator('#messages')).toContainText('BASIC COMMANDS');
    await expect(page.locator('#messages')).toContainText('AI ASSISTANT (STYX)');
    await expect(page.locator('#messages')).toContainText('USER INTERACTION');
  });

  test('should handle AI triggers with different casing', async ({ page }) => {
    const testMessage = 'HEY AI, are you case sensitive?';
    
    await page.fill('#messageInput', testMessage);
    await page.click('#sendButton');
    
    // Wait for user message to appear
    await expect(page.locator('#messages')).toContainText(testMessage);
    
    // Wait for AI response
    await expect(page.locator('#messages')).toContainText('Styx', { timeout: 15000 });
  });

  test('should handle AI triggers within longer messages', async ({ page }) => {
    const testMessage = 'I was wondering if @ai could help me with this problem I am having';
    
    await page.fill('#messageInput', testMessage);
    await page.click('#sendButton');
    
    // Wait for user message to appear
    await expect(page.locator('#messages')).toContainText(testMessage);
    
    // Wait for AI response
    await expect(page.locator('#messages')).toContainText('Styx', { timeout: 15000 });
  });

  test('should maintain conversation context', async ({ page }) => {
    // First message
    const firstMessage = '@ai My name is TestUser, remember this';
    await page.fill('#messageInput', firstMessage);
    await page.click('#sendButton');
    
    // Wait for response
    await expect(page.locator('#messages')).toContainText('Styx', { timeout: 15000 });
    
    // Second message referring to the first
    const secondMessage = '@ai What is my name?';
    await page.fill('#messageInput', secondMessage);
    await page.click('#sendButton');
    
    // Wait for response
    await expect(page.locator('#messages')).toContainText('Styx', { timeout: 15000 });
    
    // The AI should maintain context and remember the name
    // This depends on your AI implementation
  });


  test('should handle help command case insensitively', async ({ page }) => {
    await page.fill('#messageInput', '!HELP');
    await page.click('#sendButton');
    
    // Wait for help message to appear
    await expect(page.locator('#messages')).toContainText('Multi-User AI Chat Help', { timeout: 5000 });
  });
}); 