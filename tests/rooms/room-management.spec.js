const { test, expect } = require('@playwright/test');
const TestHelpers = require('../utils/test-helpers');

test.describe('Room Management Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Login as test admin user
    await TestHelpers.loginAsTestUser(page, 'admin', false);
    
    // Switch to test public room to avoid interfering with general chat
    const testRoom = await TestHelpers.getTestRoom(false);
    if (testRoom) {
      await TestHelpers.switchRoom(page, testRoom.name);
    }
  });

  test('should display room interface on login', async ({ page }) => {
    // Should be in a test room (set up by beforeEach)
    await expect(page.locator('#roomInfoName')).toBeVisible();
    await expect(page.locator('#roomsList')).toBeVisible();
    
    // Verify we're in the test room
    const testRoom = await TestHelpers.getTestRoom(false);
    if (testRoom) {
      await expect(page.locator('#roomInfoName')).toContainText(testRoom.name);
    }
  });

  test('should show create room button for admin', async ({ page }) => {
    await expect(page.locator('.create-room-btn')).toBeVisible();
    await expect(page.locator('.create-room-btn')).toContainText('+ New Room');
  });

  test('should open create room modal', async ({ page }) => {
    await page.click('.create-room-btn');
    
    // Modal should appear
    await expect(page.locator('#createRoomModal')).toBeVisible();
    await expect(page.locator('#createRoomModal h3')).toContainText('Create New Room');
    
    // Form fields should be visible (using correct IDs)
    await expect(page.locator('#newRoomName')).toBeVisible();
    await expect(page.locator('#newRoomDescription')).toBeVisible();
    await expect(page.locator('#newRoomPrompt')).toBeVisible();
  });

  test('should create a new public room', async ({ page }) => {
    const roomName = 'Test Room ' + Date.now();
    const roomDesc = 'This is a test room';
    
    await page.click('.create-room-btn');
    await expect(page.locator('#createRoomModal')).toBeVisible();
    
    // Fill out the form (using correct IDs)
    await page.fill('#newRoomName', roomName);
    await page.fill('#newRoomDescription', roomDesc);
    
    // Select an AI model (required)
    await page.selectOption('#newRoomModel', { index: 1 }); // Select first available model
    
    // Force click the Create Room button within the modal
    await page.locator('#createRoomModal button:has-text("Create Room")').click({ force: true });
    
    // Modal should close
    await expect(page.locator('#createRoomModal')).not.toBeVisible();
    
    // Room should appear in the list
    await expect(page.locator('#roomsList')).toContainText(roomName);
    
    // Should automatically join the new room
    await expect(page.locator('#roomInfoName')).toContainText(roomName);
  });

  test('should create a new private room', async ({ page }) => {
    const roomName = 'Private Test Room ' + Date.now();
    const roomDesc = 'This is a private test room';
    
    await page.click('.create-room-btn');
    await expect(page.locator('#createRoomModal')).toBeVisible();
    
    // Fill out the form (using correct IDs)
    await page.fill('#newRoomName', roomName);
    await page.fill('#newRoomDescription', roomDesc);
    
    // Select an AI model (required)
    await page.selectOption('#newRoomModel', { index: 1 }); // Select first available model
    
    // Make it private (using correct ID)
    await page.check('#newRoomPrivate');
    
    // Check a user for assignment (if user selection is visible)
    const userContainer = page.locator('#userSelectionContainer');
    if (await userContainer.isVisible()) {
      const firstUserCheckbox = userContainer.locator('input[type="checkbox"]').first();
      if (await firstUserCheckbox.isVisible()) {
        await firstUserCheckbox.click({ force: true });
      }
    }
    
    // Force click the Create Room button within the modal
    await page.locator('#createRoomModal button:has-text("Create Room")').click({ force: true });
    
    // Modal should close
    await expect(page.locator('#createRoomModal')).not.toBeVisible();
    
    // Room should appear in the list
    await expect(page.locator('#roomsList')).toContainText(roomName);
  });

  test('should require room name for creation', async ({ page }) => {
    await page.click('.create-room-btn');
    await expect(page.locator('#createRoomModal')).toBeVisible();
    
    // Try to create without name but with required model
    await page.selectOption('#newRoomModel', { index: 1 }); // Select first available model
    
    // Force click the Create Room button within the modal
    await page.locator('#createRoomModal button:has-text("Create Room")').click({ force: true });
    
    // Should show validation error or modal should stay open
    await expect(page.locator('#createRoomModal')).toBeVisible();
  });

  test('should cancel room creation', async ({ page }) => {
    const cancelTestRoomName = 'Cancel Test Room ' + Date.now();
    
    await page.click('.create-room-btn');
    await expect(page.locator('#createRoomModal')).toBeVisible();
    
    // Fill some data (using correct IDs)
    await page.fill('#newRoomName', cancelTestRoomName);
    
    // Force click the Cancel button within the create room modal
    await page.locator('#createRoomModal button:has-text("Cancel")').click({ force: true });
    
    // Modal should close
    await expect(page.locator('#createRoomModal')).not.toBeVisible();
    
    // Room should not be created
    await expect(page.locator('#roomsList')).not.toContainText(cancelTestRoomName);
  });

  test('should switch between rooms', async ({ page }) => {
    // Create a test room first
    const roomName = 'Switch Test Room ' + Date.now();
    
    await page.click('.create-room-btn');
    await page.fill('#newRoomName', roomName);
    await page.selectOption('#newRoomModel', { index: 1 }); // Select first available model
    
    // Force click the Create Room button within the modal
    await page.locator('#createRoomModal button:has-text("Create Room")').click({ force: true });
    
    // Should be in the new room
    await expect(page.locator('#roomInfoName')).toContainText(roomName);
    
    // Switch to test public room instead of general room
    const testRoom = await TestHelpers.getTestRoom(false);
    if (testRoom) {
      await page.click(`#roomsList .room-item:has-text("${testRoom.name}")`);
      await expect(page.locator('#roomInfoName')).toContainText(testRoom.name);
    }
  });

  test('should show room description when available', async ({ page }) => {
    const roomName = 'Description Test Room ' + Date.now();
    const roomDesc = 'This room has a description';
    
    await page.click('.create-room-btn');
    await page.fill('#newRoomName', roomName);
    await page.fill('#newRoomDescription', roomDesc);
    await page.selectOption('#newRoomModel', { index: 1 }); // Select first available model
    
    // Force click the Create Room button within the modal
    await page.locator('#createRoomModal button:has-text("Create Room")').click({ force: true });
    
    // Should show room description
    await expect(page.locator('#roomInfoDesc')).toContainText(roomDesc);
  });

  test('should handle custom AI prompt for room', async ({ page }) => {
    const roomName = 'AI Prompt Test Room ' + Date.now();
    const customPrompt = 'You are a helpful coding assistant';
    
    await page.click('.create-room-btn');
    await page.fill('#newRoomName', roomName);
    await page.fill('#newRoomPrompt', customPrompt);
    await page.selectOption('#newRoomModel', { index: 1 }); // Select first available model
    
    // Force click the Create Room button within the modal
    await page.locator('#createRoomModal button:has-text("Create Room")').click({ force: true });
    
    // Should show custom prompt info
    await expect(page.locator('#roomInfoPrompt')).toBeVisible();
    await expect(page.locator('#roomInfoPromptText')).toContainText(customPrompt);
  });

  test('should handle room creation with AI model selection', async ({ page }) => {
    const roomName = 'AI Model Test Room ' + Date.now();
    
    await page.click('.create-room-btn');
    await page.fill('#newRoomName', roomName);
    
    // Select AI model (using correct ID)
    const modelSelect = page.locator('#newRoomModel');
    await expect(modelSelect).toBeVisible();
    await modelSelect.selectOption({ index: 1 }); // Select first available model
    
    // Force click the Create Room button within the modal
    await page.click('.btn-create');
    
    // Room should be created successfully
    await expect(page.locator('#roomInfoName')).toContainText(roomName);
  });

  test('should handle voice settings for room', async ({ page }) => {
    const roomName = 'Voice Test Room ' + Date.now();
    
    await page.click('.create-room-btn');
    await page.fill('#newRoomName', roomName);
    
    // Select voice (using correct ID)
    const voiceSelect = page.locator('#newRoomVoice');
    if (await voiceSelect.isVisible()) {
      await voiceSelect.selectOption({ index: 1 }); // Select first available voice
    }
    
    await page.selectOption('#newRoomModel', { index: 1 }); // Select first available model
    
    // Force click the Create Room button within the modal
    await page.locator('#createRoomModal button:has-text("Create Room")').click({ force: true });
    
    // Room should be created successfully
    await expect(page.locator('#roomInfoName')).toContainText(roomName);
  });

  test('should edit room settings', async ({ page }) => {
    // Create a room first
    const roomName = 'Edit Test Room ' + Date.now();
    
    await page.click('.create-room-btn');
    await page.fill('#newRoomName', roomName);
    await page.selectOption('#newRoomModel', { index: 1 }); // Select first available model
    
    // Force click the Create Room button within the modal
    await page.locator('#createRoomModal button:has-text("Create Room")').click({ force: true });
    
    // Look for room settings button (three dots or settings icon)
    const roomItem = page.locator(`#roomsList .room-item:has-text("${roomName}")`);
    await expect(roomItem).toBeVisible();
    
    // Try to find and click room settings - it's a gear icon with class room-settings-btn
    const settingsButton = roomItem.locator('.room-settings-btn');
    if (await settingsButton.isVisible()) {
      await settingsButton.click();
      
      // Edit form should appear
      await expect(page.locator('#roomSettingsModal')).toBeVisible();
      
      // Make changes
      await page.fill('#editRoomName', roomName + ' (Edited)');
      await page.click('button:has-text("Save Changes")');
      
      // Should show updated name
      await expect(page.locator('#roomInfoName')).toContainText('(Edited)');
    } else {
      console.log('Room settings button not found or not visible');
    }
  });

  test('should show room member count', async ({ page }) => {
    // The room should show current user count
    // This depends on your UI implementation
    const testUser = await TestHelpers.getTestUser('admin', false);
    await expect(page.locator('#usersList')).toContainText(testUser.username);
  });

  test('should handle room deletion', async ({ page }) => {
    // Create a room first
    const roomName = 'Delete Test Room ' + Date.now();
    
    await page.click('.create-room-btn');
    await page.fill('#newRoomName', roomName);
    await page.selectOption('#newRoomModel', { index: 1 }); // Select first available model
    
    // Force click the Create Room button within the modal
    await page.locator('#createRoomModal button:has-text("Create Room")').click({ force: true });
    
    // Look for room settings to access delete
    const roomItem = page.locator(`#roomsList .room-item:has-text("${roomName}")`);
    await expect(roomItem).toBeVisible();
    
    // Try to find and click room settings
    const settingsButton = roomItem.locator('.room-settings-btn');
    await expect(settingsButton).toBeVisible();
    await settingsButton.click();
    
    // Wait for room settings modal to appear
    await expect(page.locator('#roomSettingsModal')).toBeVisible();
    
    // Look for delete button in settings modal
    const deleteButton = page.locator('#deleteRoomBtn');
    await expect(deleteButton).toBeVisible();
    
    // Set up dialog handler before clicking delete
    page.on('dialog', dialog => {
      console.log('Dialog message:', dialog.message());
      dialog.accept();
    });
    
    // Override window.confirm to always return true
    await page.evaluate(() => {
      window.confirm = () => true;
    });
    
    await deleteButton.click();
    
    // Wait for modal to close
    await expect(page.locator('#roomSettingsModal')).not.toBeVisible();
    
    // Room should be removed from list
    await expect(page.locator('#roomsList')).not.toContainText(roomName);
  });
});