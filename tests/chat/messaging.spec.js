const { test, expect } = require('@playwright/test');
const TestHelpers = require('../utils/test-helpers');

test.describe('Chat Messaging Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Login as test admin user
    await TestHelpers.loginAsTestUser(page, 'admin', false);
    
    // Switch to test public room to avoid interfering with general chat
    const testRoom = await TestHelpers.getTestRoom(false); // Get public test room
    if (testRoom) {
      await TestHelpers.switchRoom(page, testRoom.name);
    }
  });

  test('should display chat interface after login', async ({ page }) => {
    await expect(page.locator('#chatContainer')).toBeVisible();
    await expect(page.locator('#messages')).toBeVisible();
    await expect(page.locator('#messageInput')).toBeVisible();
    await expect(page.locator('#sendButton')).toBeVisible();
    await expect(page.locator('#usersList')).toBeVisible();
  });

  test('should send a message successfully', async ({ page }) => {
    const testMessage = 'Test message ' + Date.now();
    
    await page.fill('#messageInput', testMessage);
    await page.click('#sendButton');
    
    // Message input should be cleared
    await expect(page.locator('#messageInput')).toHaveValue('');
    
    // Message should appear in chat
    await expect(page.locator('#messages')).toContainText(testMessage);
  });

  test('should send message with Enter key', async ({ page }) => {
    const testMessage = 'Test message via Enter ' + Date.now();
    
    await page.fill('#messageInput', testMessage);
    await page.press('#messageInput', 'Enter');
    
    // Message should appear in chat
    await expect(page.locator('#messages')).toContainText(testMessage);
  });

  test('should not send empty messages', async ({ page }) => {
    // Clear messages from current room for clean test state
    await TestHelpers.clearCurrentRoomMessages(page);
    
    // Wait a moment for clearing to complete
    await page.waitForTimeout(500);
    
    // Get initial message count (should be 0 after clearing)
    const initialMessageCount = await page.locator('#messages .message').count();
    
    // Try to send empty message
    await page.click('#sendButton');
    
    // Wait a moment to ensure no message is sent
    await page.waitForTimeout(500);
    
    // Message count should not change
    await expect(page.locator('#messages .message')).toHaveCount(initialMessageCount);
  });

  test('should not send messages with only whitespace', async ({ page }) => {
    // Clear messages from current room for clean test state
    await TestHelpers.clearCurrentRoomMessages(page);
    
    // Wait a moment for clearing to complete
    await page.waitForTimeout(500);
    
    // Get initial message count (should be 0 after clearing)
    const initialMessageCount = await page.locator('#messages .message').count();
    
    // Try to send whitespace-only message
    await page.fill('#messageInput', '   ');
    await page.click('#sendButton');
    
    // Wait a moment to ensure no message is sent
    await page.waitForTimeout(500);
    
    // Message count should not change
    await expect(page.locator('#messages .message')).toHaveCount(initialMessageCount);
  });

  test('should display user online status', async ({ page }) => {
    const testUser = await TestHelpers.getTestUser('admin', false);
    await expect(page.locator('#usersList')).toBeVisible();
    await expect(page.locator('#usersList')).toContainText(testUser.username);
  });

  test('should show current user name in header', async ({ page }) => {
    const testUser = await TestHelpers.getTestUser('admin', false);
    await expect(page.locator('#currentUserName')).toContainText(testUser.username);
  });

  test('should handle long messages', async ({ page }) => {
    const longMessage = 'A'.repeat(1000) + ' ' + Date.now();
    
    await page.fill('#messageInput', longMessage);
    await page.click('#sendButton');
    
    // Message should appear in chat
    await expect(page.locator('#messages')).toContainText(longMessage);
  });

  test('should handle messages with special characters', async ({ page }) => {
    const specialMessage = 'Test with special chars: @#$%^&*()_+{}|:<>?[]\\;\'",./~`' + Date.now();
    
    await page.fill('#messageInput', specialMessage);
    await page.click('#sendButton');
    
    // Message should appear in chat
    await expect(page.locator('#messages')).toContainText(specialMessage);
  });

  test('should load message history on connect', async ({ page }) => {
    // Send a message first
    const testMessage = 'History test message ' + Date.now();
    await page.fill('#messageInput', testMessage);
    await page.click('#sendButton');
    
    // Wait for message to appear
    await expect(page.locator('#messages')).toContainText(testMessage);
    
    // Refresh the page (reconnect)
    await page.reload();
    
    // Login again as test admin user
    await TestHelpers.loginAsTestUser(page, 'admin', false);
    
    // Switch back to test public room (this was missing!)
    const testRoom = await TestHelpers.getTestRoom(false);
    if (testRoom) {
      await TestHelpers.switchRoom(page, testRoom.name);
    }
    
    // Message history should be loaded
    await expect(page.locator('#messages')).toContainText(testMessage);
  });

  test('should display message timestamps', async ({ page }) => {
    const testMessage = 'Timestamp test ' + Date.now();
    
    await page.fill('#messageInput', testMessage);
    await page.click('#sendButton');
    
    // Wait for message to appear
    await expect(page.locator('#messages')).toContainText(testMessage);
    
    // Check for timestamp (messages should have timestamp elements with .message-time class)
    await expect(page.locator('#messages .message .message-time').first()).toBeVisible();
  });


  test('should maintain scroll position with new messages', async ({ page }) => {
    // Send multiple messages to create scrollable content
    for (let i = 0; i < 10; i++) {
      await page.fill('#messageInput', `Test message ${i} ${Date.now()}`);
      await page.click('#sendButton');
      await page.waitForTimeout(100);
    }
    
    // Messages container should be scrollable
    const messagesContainer = page.locator('#messages');
    await expect(messagesContainer).toBeVisible();
    
    // Scroll should be at bottom (newest messages)
    const scrollTop = await messagesContainer.evaluate(el => el.scrollTop);
    const scrollHeight = await messagesContainer.evaluate(el => el.scrollHeight);
    const clientHeight = await messagesContainer.evaluate(el => el.clientHeight);
    
    expect(scrollTop).toBeGreaterThan(scrollHeight - clientHeight - 50); // Allow small margin
  });

  test('should handle connection status display', async ({ page }) => {
    // Should show connected status
    await expect(page.locator('#status')).toContainText('Connected');
    
    // Status should be visible
    await expect(page.locator('#status')).toBeVisible();
  });
}); 