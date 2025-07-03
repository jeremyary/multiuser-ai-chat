const { expect } = require('@playwright/test');
const fs = require('fs').promises;
const path = require('path');

/**
 * Test utility functions for the AI Chat application
 */
class TestHelpers {
  /**
   * Load test data created during global setup
   * @returns {Promise<Object>} Test data with users and rooms
   */
  static async getTestData() {
    try {
      const testDataPath = path.join(__dirname, '..', 'test-data.json');
      const testDataContent = await fs.readFile(testDataPath, 'utf-8');
      return JSON.parse(testDataContent);
    } catch (error) {
      console.warn('Warning: Could not load test data, using defaults');
      return { users: [], rooms: [] };
    }
  }

  /**
   * Get a test user by persona type
   * @param {string} role - User role (user, admin)
   * @param {boolean} isKid - Whether to get a kid account
   * @returns {Promise<Object|null>} Test user data
   */
  static async getTestUser(role = 'user', isKid = false) {
    const testData = await this.getTestData();
    return testData.users.find(user => 
      user.role === role && user.is_kid_account === isKid
    ) || null;
  }

  /**
   * Get a test room by privacy setting
   * @param {boolean} isPrivate - Whether to get a private room
   * @returns {Promise<Object|null>} Test room data
   */
  static async getTestRoom(isPrivate = false) {
    const testData = await this.getTestData();
    return testData.rooms.find(room => room.is_private === isPrivate) || null;
  }
  /**
   * Login with provided credentials
   * @param {Page} page - Playwright page object
   * @param {string} username - Username to login with
   * @param {string} password - Password to login with
   */
  static async login(page, username = 'admin', password = 'admin123!') {
    await page.goto('/');
    await page.fill('#username', username);
    await page.fill('#password', password);
    await page.waitForTimeout(200); // Small delay to ensure form is ready
    await page.click('button:has-text("Login")');
    
    // Wait for successful login
    await expect(page.locator('#chatContainer')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#messageInput')).toBeEnabled();
  }

  /**
   * Login as a test user
   * @param {Page} page - Playwright page object
   * @param {string} role - User role (user, admin, moderator)
   * @param {boolean} isKid - Whether to login as a kid account
   */
  static async loginAsTestUser(page, role = 'user', isKid = false) {
    const testUser = await this.getTestUser(role, isKid);
    if (!testUser) {
      throw new Error(`No test user found for role: ${role}, isKid: ${isKid}`);
    }
    
    await this.login(page, testUser.username, testUser.password);
    return testUser;
  }

  /**
   * Logout from the application
   * @param {Page} page - Playwright page object
   */
  static async logout(page) {
    await page.click('button:has-text("Logout")');
    await expect(page.locator('#loginContainer')).toBeVisible();
    await expect(page.locator('#chatContainer')).not.toBeVisible();
  }

  /**
   * Send a message in the chat
   * @param {Page} page - Playwright page object
   * @param {string} message - Message to send
   */
  static async sendMessage(page, message) {
    await page.fill('#messageInput', message);
    await page.click('#sendButton');
    
    // Wait for message to appear
    await expect(page.locator('#messages')).toContainText(message);
  }

  /**
   * Wait for AI response from Styx
   * @param {Page} page - Playwright page object
   * @param {number} timeout - Timeout in milliseconds
   */
  static async waitForAIResponse(page, timeout = 15000) {
    await expect(page.locator('#messages')).toContainText('Styx', { timeout });
  }

  /**
   * Create a new room
   * @param {Page} page - Playwright page object
   * @param {Object} roomData - Room configuration
   */
  static async createRoom(page, roomData) {
    const {
      name,
      description = '',
      isPrivate = false,
      aiPrompt = '',
      aiModel = '',
      voiceEnabled = false
    } = roomData;

    await page.click('.create-room-btn');
    await expect(page.locator('#createRoomModal')).toBeVisible();
    
    // Use correct form field IDs
    await page.fill('#newRoomName', name);
    if (description) {
      await page.fill('#newRoomDescription', description);
    }
    if (aiPrompt) {
      await page.fill('#newRoomPrompt', aiPrompt);
    }
    
    // Select AI model (required)
    if (aiModel) {
      await page.selectOption('#newRoomModel', aiModel);
    } else {
      await page.selectOption('#newRoomModel', { index: 1 }); // Select first available model
    }
    
    if (isPrivate) {
      await page.check('#newRoomPrivate');
      
      // Check a user for assignment (if user selection is visible)
      const userContainer = page.locator('#userSelectionContainer');
      if (await userContainer.isVisible()) {
        const firstUserCheckbox = userContainer.locator('input[type="checkbox"]').first();
        if (await firstUserCheckbox.isVisible()) {
          await firstUserCheckbox.check();
        }
      }
    }
    
    if (voiceEnabled) {
      const voiceSelect = page.locator('#newRoomVoice');
      if (await voiceSelect.isVisible()) {
        await voiceSelect.selectOption({ index: 1 }); // Select first available voice
      }
    }
    
    await page.click('button:has-text("Create Room")');
    await expect(page.locator('#createRoomModal')).not.toBeVisible();
    
    // Verify room was created
    await expect(page.locator('#roomsList')).toContainText(name);
    await expect(page.locator('#roomInfoName')).toContainText(name);
  }

  /**
   * Switch to a specific room
   * @param {Page} page - Playwright page object
   * @param {string} roomName - Name of the room to switch to
   */
  static async switchRoom(page, roomName) {
    await page.waitForTimeout(500);
    await page.click(`#roomsList .room-item:has-text("${roomName}")`);
    await expect(page.locator('#roomInfoName')).toContainText(roomName);
  }

  /**
   * Open mobile menu (for mobile viewports)
   * @param {Page} page - Playwright page object
   */
  static async openMobileMenu(page) {
    await page.click('.mobile-menu-toggle');
    await expect(page.locator('#usersPanel')).toBeVisible();
  }

  /**
   * Close mobile menu (for mobile viewports)
   * @param {Page} page - Playwright page object
   */
  static async closeMobileMenu(page) {
    await page.click('.mobile-menu-close');
    await expect(page.locator('#usersPanel')).not.toBeVisible();
  }

  /**
   * Set viewport to mobile size
   * @param {Page} page - Playwright page object
   * @param {Object} size - Viewport size {width, height}
   */
  static async setMobileViewport(page, size = { width: 375, height: 667 }) {
    await page.setViewportSize(size);
  }

  /**
   * Set viewport to desktop size
   * @param {Page} page - Playwright page object
   * @param {Object} size - Viewport size {width, height}
   */
  static async setDesktopViewport(page, size = { width: 1920, height: 1080 }) {
    await page.setViewportSize(size);
  }

  /**
   * Wait for WebSocket connection
   * @param {Page} page - Playwright page object
   */
  static async waitForWebSocketConnection(page) {
    await expect(page.locator('#status')).toContainText('Connected');
  }

  /**
   * Generate a unique test identifier
   * @param {string} prefix - Prefix for the identifier
   * @returns {string} Unique identifier
   */
  static generateTestId(prefix = 'test') {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Wait for element to be visible and enabled
   * @param {Page} page - Playwright page object
   * @param {string} selector - CSS selector
   * @param {number} timeout - Timeout in milliseconds
   */
  static async waitForElementReady(page, selector, timeout = 5000) {
    await expect(page.locator(selector)).toBeVisible({ timeout });
    await expect(page.locator(selector)).toBeEnabled({ timeout });
  }

  /**
   * Check if element exists without throwing error
   * @param {Page} page - Playwright page object
   * @param {string} selector - CSS selector
   * @returns {Promise<boolean>} Whether element exists
   */
  static async elementExists(page, selector) {
    try {
      await page.locator(selector).waitFor({ state: 'attached', timeout: 1000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Trigger AI response by sending message with trigger
   * @param {Page} page - Playwright page object
   * @param {string} message - Message to send (should contain AI trigger)
   * @param {number} timeout - Timeout for AI response
   */
  static async triggerAIResponse(page, message, timeout = 15000) {
    await this.sendMessage(page, message);
    await this.waitForAIResponse(page, timeout);
  }

  /**
   * Get message count in chat
   * @param {Page} page - Playwright page object
   * @returns {Promise<number>} Number of messages
   */
  static async getMessageCount(page) {
    return await page.locator('#messages .message').count();
  }

  /**
   * Get list of online users
   * @param {Page} page - Playwright page object
   * @returns {Promise<string[]>} List of user names
   */
  static async getOnlineUsers(page) {
    const userElements = await page.locator('#usersList .user-item').all();
    const users = [];
    for (const element of userElements) {
      const userName = await element.textContent();
      users.push(userName?.trim() || '');
    }
    return users;
  }

  /**
   * Get list of available rooms
   * @param {Page} page - Playwright page object
   * @returns {Promise<string[]>} List of room names
   */
  static async getAvailableRooms(page) {
    const roomElements = await page.locator('#roomsList .room-item').all();
    const rooms = [];
    for (const element of roomElements) {
      const roomName = await element.textContent();
      rooms.push(roomName?.trim() || '');
    }
    return rooms;
  }

  /**
   * Clear chat messages (if functionality exists)
   * @param {Page} page - Playwright page object
   */
  static async clearMessages(page) {
    const clearButton = page.locator('.clear-messages-btn, button:has-text("Clear")');
    if (await clearButton.isVisible()) {
      await clearButton.click();
    }
  }

  /**
   * Clear all messages from a room via API (admin only)
   * @param {string} roomId - Room ID to clear messages from
   * @param {string} adminToken - Admin authentication token
   * @param {string} baseURL - Base URL for API requests
   * @returns {Promise<boolean>} Whether the operation was successful
   */
  static async clearRoomMessages(roomId, adminToken, baseURL = 'https://localhost:3443') {
    try {
      const { request } = require('@playwright/test');
      const apiContext = await request.newContext({
        baseURL: baseURL,
        ignoreHTTPSErrors: true
      });

      const response = await apiContext.delete(`/rooms/${roomId}/messages`, {
        headers: {
          'Authorization': `Bearer ${adminToken}`
        }
      });

      await apiContext.dispose();
      
      if (response.ok()) {
        console.log(`  ✅ Cleared messages from room: ${roomId}`);
        return true;
      } else {
        console.log(`  ❌ Failed to clear messages from room ${roomId}: ${response.status()}`);
        return false;
      }
    } catch (error) {
      console.log(`  ❌ Error clearing messages from room ${roomId}: ${error.message}`);
      return false;
    }
  }

  /**
   * Clear messages from the current room for clean test state
   * Only works with test rooms - will not affect the general room
   * @param {Page} page - Playwright page object
   * @returns {Promise<boolean>} Whether the operation was successful
   */
  static async clearCurrentRoomMessages(page) {
    try {
      const testData = await this.getTestData();
      if (!testData.adminToken) {
        console.log('  ❌ No admin token available for clearing messages');
        return false;
      }
      
      // Get current room name from the page
      const currentRoomName = await page.locator('#roomInfoName').textContent();
      if (!currentRoomName) {
        console.log('  ❌ Could not determine current room name');
        return false;
      }
      
      // Only clear messages from test rooms - never from general room
      const testRooms = testData.rooms || [];
      const currentRoom = testRooms.find(room => room.name === currentRoomName.trim());
      
      if (currentRoom) {
        return await this.clearRoomMessages(currentRoom.id, testData.adminToken);
      } else {
        console.log(`  ❌ Room '${currentRoomName}' is not a test room - message clearing skipped`);
        return false;
      }
    } catch (error) {
      console.log(`  ❌ Error clearing current room messages: ${error.message}`);
      return false;
    }
  }

  /**
   * Take screenshot for debugging
   * @param {Page} page - Playwright page object
   * @param {string} name - Screenshot name
   */
  static async takeDebugScreenshot(page, name) {
    await page.screenshot({ path: `tests/debug-screenshots/${name}.png` });
  }

  /**
   * Wait for loading to complete
   * @param {Page} page - Playwright page object
   */
  static async waitForLoadingComplete(page) {
    // Wait for any loading indicators to disappear
    await page.waitForLoadState('networkidle');
    
    // Wait for common loading elements to disappear
    const loadingSelectors = ['.loading', '.spinner', '.loader', '[data-loading]'];
    for (const selector of loadingSelectors) {
      const element = page.locator(selector);
      if (await element.isVisible()) {
        await element.waitFor({ state: 'hidden', timeout: 10000 });
      }
    }
  }

  /**
   * Verify application is fully loaded and ready
   * @param {Page} page - Playwright page object
   */
  static async verifyAppReady(page) {
    await this.waitForLoadingComplete(page);
    await expect(page.locator('#chatContainer')).toBeVisible();
    await expect(page.locator('#messageInput')).toBeEnabled();
    await this.waitForWebSocketConnection(page);
  }

  /**
   * Handle alerts and dialogs
   * @param {Page} page - Playwright page object
   * @param {string} action - 'accept' or 'dismiss'
   */
  static async handleDialog(page, action = 'accept') {
    page.on('dialog', async dialog => {
      if (action === 'accept') {
        await dialog.accept();
      } else {
        await dialog.dismiss();
      }
    });
  }

  /**
   * Mock network responses for testing
   * @param {Page} page - Playwright page object
   * @param {string} url - URL pattern to mock
   * @param {Object} response - Mock response data
   */
  static async mockNetworkResponse(page, url, response) {
    await page.route(url, route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(response)
      });
    });
  }
}

module.exports = TestHelpers; 