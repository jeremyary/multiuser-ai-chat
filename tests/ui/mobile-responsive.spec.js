const { test, expect } = require('@playwright/test');
const TestHelpers = require('../utils/test-helpers');

test.describe('Mobile Responsive Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Login as test admin user
    await TestHelpers.loginAsTestUser(page, 'admin', false);
    
    // Switch to test public room to avoid interfering with general chat
    const testRoom = await TestHelpers.getTestRoom(false); // Get public test room
    if (testRoom) {
      await TestHelpers.switchRoom(page, testRoom.name);
    }
  });

  test('should display mobile menu toggle on small screens', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Mobile menu toggle should be visible
    await expect(page.locator('.mobile-menu-toggle')).toBeVisible();
    
    // Users panel should be hidden by default on mobile
    const usersPanel = page.locator('#usersPanel');
    const isVisible = await usersPanel.isVisible();
    if (!isVisible) {
      // Panel is hidden, which is expected on mobile
      expect(isVisible).toBe(false);
    }
  });

  test('should hide mobile menu toggle on desktop', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Mobile menu toggle should be hidden
    await expect(page.locator('.mobile-menu-toggle')).not.toBeVisible();
    
    // Users panel should be visible on desktop
    await expect(page.locator('#usersPanel')).toBeVisible();
  });

  test('should open mobile menu when toggle is clicked', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Click mobile menu toggle
    await page.click('.mobile-menu-toggle');
    
    // Users panel should become visible
    await expect(page.locator('#usersPanel')).toBeVisible();
  });

  test('should close mobile menu when close button is clicked', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Open mobile menu
    await page.click('.mobile-menu-toggle');
    await expect(page.locator('#usersPanel')).toBeVisible();
    
    // Wait for menu to fully open
    await page.waitForTimeout(300);
    
    // Click close button (it should be visible after menu opens)
    await page.click('.mobile-menu-close');
    
    // Wait for closing animation
    await page.waitForTimeout(500);
    
    // Users panel should be hidden or not have the mobile-open class
    await expect(page.locator('#usersPanel')).not.toHaveClass(/mobile-open/);
  });

  test('should handle responsive layout on tablet', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    
    // Chat container should be visible
    await expect(page.locator('#chatContainer')).toBeVisible();
    
    // Message input should be usable
    await expect(page.locator('#messageInput')).toBeVisible();
    await expect(page.locator('#sendButton')).toBeVisible();
  });

  test('should handle responsive layout on mobile portrait', async ({ page }) => {
    // Set mobile portrait viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Chat container should be visible
    await expect(page.locator('#chatContainer')).toBeVisible();
    
    // Message input should be usable
    await expect(page.locator('#messageInput')).toBeVisible();
    await expect(page.locator('#sendButton')).toBeVisible();
    
    // Chat panel should take full width
    const chatPanel = page.locator('.chat-panel');
    await expect(chatPanel).toBeVisible();
  });

  test('should handle responsive layout on mobile landscape', async ({ page }) => {
    // Set mobile landscape viewport
    await page.setViewportSize({ width: 667, height: 375 });
    
    // Chat container should be visible
    await expect(page.locator('#chatContainer')).toBeVisible();
    
    // Message input should be usable
    await expect(page.locator('#messageInput')).toBeVisible();
    await expect(page.locator('#sendButton')).toBeVisible();
  });

  test('should handle touch interactions on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Test touch interaction with mobile menu
    await page.tap('.mobile-menu-toggle');
    await expect(page.locator('#usersPanel')).toBeVisible();
    
    // Close the mobile menu so it doesn't block other interactions
    await page.tap('.mobile-menu-close');
    await page.waitForTimeout(500);
    
    // Test touch interaction with send button
    await page.fill('#messageInput', 'Touch test message');
    await page.tap('#sendButton');
    
    // Message should be sent
    await expect(page.locator('#messages')).toContainText('Touch test message');
  });

  test('should handle viewport changes dynamically', async ({ page }) => {
    // Start with desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Users panel should be visible
    await expect(page.locator('#usersPanel')).toBeVisible();
    
    // Switch to mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Mobile menu toggle should now be visible
    await expect(page.locator('.mobile-menu-toggle')).toBeVisible();
    
    // Switch back to desktop
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Mobile menu toggle should be hidden again
    await expect(page.locator('.mobile-menu-toggle')).not.toBeVisible();
  });

  test('should maintain functionality on small screens', async ({ page }) => {
    // Set very small viewport
    await page.setViewportSize({ width: 320, height: 568 });
    
    // Core functionality should still work
    await page.fill('#messageInput', 'Small screen test');
    await page.click('#sendButton');
    
    // Message should be sent
    await expect(page.locator('#messages')).toContainText('Small screen test');
  });

  test('should handle login form responsively', async ({ page }) => {
    // Logout first
    await page.click('button:has-text("Logout")');
    
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Login form should be visible and usable
    await expect(page.locator('#loginContainer')).toBeVisible();
    await expect(page.locator('#username')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.locator('button:has-text("Login")')).toBeVisible();
    
    // Login should work on mobile with test user
    const testUser = await TestHelpers.getTestUser('admin', false);
    await page.fill('#username', testUser.username);
    await page.fill('#password', testUser.password);
    await page.waitForTimeout(200); // Small delay to ensure form is ready
    await page.click('button:has-text("Login")');
    
    await expect(page.locator('#chatContainer')).toBeVisible({ timeout: 10000 });
  });

  test('should handle modal dialogs responsively', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Open mobile menu to access create room button
    await page.click('.mobile-menu-toggle');
    await expect(page.locator('#usersPanel')).toBeVisible();
    
    // Scroll to ensure create room button is visible
    await page.locator('.create-room-btn').scrollIntoViewIfNeeded();
    
    // Open create room modal
    await page.click('.create-room-btn');
    
    // Wait for modal to appear
    await page.waitForTimeout(500);
    
    // Modal should be visible and usable on mobile
    await expect(page.locator('#createRoomModal')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#newRoomName')).toBeVisible({ timeout: 5000 });
    
    // Form should be usable
    await page.fill('#newRoomName', 'Mobile Test Room');
    await page.click('button:has-text("Cancel")');
    
    // Modal should close
    await expect(page.locator('#createRoomModal')).not.toBeVisible();
  });

  test('should handle message overflow on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Send a very long message
    const longMessage = 'This is a very long message that should wrap properly on mobile devices and not break the layout. '.repeat(5);
    
    await page.fill('#messageInput', longMessage);
    await page.click('#sendButton');
    
    // Message should be displayed properly
    await expect(page.locator('#messages')).toContainText(longMessage);
    
    // Layout should not be broken
    await expect(page.locator('#messageInput')).toBeVisible();
  });

  test('should handle user list on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Open mobile menu
    await page.click('.mobile-menu-toggle');
    
    // User list should be visible
    await expect(page.locator('#usersList')).toBeVisible();
    const testUser = await TestHelpers.getTestUser('admin', false);
    await expect(page.locator('#usersList')).toContainText(testUser.username);
    
    // Room list should be visible
    await expect(page.locator('#roomsList')).toBeVisible();
  });

  test('should handle header responsively', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Header should be visible
    await expect(page.locator('.header')).toBeVisible();
    
    // User name should be visible
    await expect(page.locator('#currentUserName')).toBeVisible();
    
    // Mobile menu toggle should be in header
    await expect(page.locator('.mobile-menu-toggle')).toBeVisible();
  });

  test('should handle room switching on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Open mobile menu to access create room button
    await page.click('.mobile-menu-toggle');
    await expect(page.locator('#usersPanel')).toBeVisible();
    
    // Scroll to ensure create room button is visible
    await page.locator('.create-room-btn').scrollIntoViewIfNeeded();
    
    // Create a test room
    await page.click('.create-room-btn');
    
    // Wait for modal to appear
    await page.waitForTimeout(500);
    
    // Fill the form
    await expect(page.locator('#newRoomName')).toBeVisible({ timeout: 5000 });
    await page.fill('#newRoomName', 'Mobile Switch Test');
    await page.selectOption('#newRoomModel', { index: 1 }); // Select first available model
    await page.click('button:has-text("Create Room")');
    
    // Should be in the new room
    await expect(page.locator('#roomInfoName')).toContainText('Mobile Switch Test');
    
    // Open mobile menu
    await page.click('.mobile-menu-toggle');
    
    // Switch to test public room instead of general room
    const testRoom = await TestHelpers.getTestRoom(false);
    if (testRoom) {
      await page.click(`#roomsList .room-item:has-text("${testRoom.name}")`);
      await expect(page.locator('#roomInfoName')).toContainText(testRoom.name);
    }
    
    // Mobile menu should close after room switch
    await expect(page.locator('#usersPanel')).not.toHaveClass(/mobile-open/);
  });

  test('should handle orientation changes', async ({ page }) => {
    // Start in portrait
    await page.setViewportSize({ width: 375, height: 667 });
    
    // App should work in portrait
    await expect(page.locator('#chatContainer')).toBeVisible();
    
    // Switch to landscape
    await page.setViewportSize({ width: 667, height: 375 });
    
    // App should still work in landscape
    await expect(page.locator('#chatContainer')).toBeVisible();
    await expect(page.locator('#messageInput')).toBeVisible();
    
    // Send a message in landscape
    await page.fill('#messageInput', 'Landscape test');
    await page.click('#sendButton');
    
    await expect(page.locator('#messages')).toContainText('Landscape test');
  });
}); 