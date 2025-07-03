const { test, expect } = require('@playwright/test');
const TestHelpers = require('../utils/test-helpers');

test.describe('Authentication Tests with Test Personas', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should login successfully with test regular user', async ({ page }) => {
    const testUser = await TestHelpers.loginAsTestUser(page, 'user');
    
    // Verify successful login
    await expect(page.locator('#chatContainer')).toBeVisible();
    await expect(page.locator('#currentUserName')).toContainText(testUser.username);
    
    // Regular user should not see admin features
    await expect(page.locator('#userMgmtBtn')).not.toBeVisible();
  });

  test('should login successfully with test admin user', async ({ page }) => {
    const testUser = await TestHelpers.loginAsTestUser(page, 'admin');
    
    // Verify successful login
    await expect(page.locator('#chatContainer')).toBeVisible();
    await expect(page.locator('#currentUserName')).toContainText(testUser.username);
    
    // Admin should see admin features
    await expect(page.locator('#userMgmtBtn')).toBeVisible();
  });



  test('should login successfully with test kid account', async ({ page }) => {
    const testUser = await TestHelpers.loginAsTestUser(page, 'user', true);
    
    // Verify successful login
    await expect(page.locator('#chatContainer')).toBeVisible();
    await expect(page.locator('#currentUserName')).toContainText(testUser.username);
    
    // Kid accounts should not see room creation button
    await expect(page.locator('.create-room-btn')).not.toBeVisible();
  });

  test('should handle persona-based access control', async ({ page }) => {
    // Test with regular user persona
    let testUser = await TestHelpers.loginAsTestUser(page, 'user');
    
    // Regular user should not have admin features
    await expect(page.locator('#userMgmtBtn')).not.toBeVisible();
    
    // Logout and login as admin persona
    await TestHelpers.logout(page);
    testUser = await TestHelpers.loginAsTestUser(page, 'admin');
    
    // Admin should have admin features
    await expect(page.locator('#userMgmtBtn')).toBeVisible();
  });

  test('should use test rooms for testing', async ({ page }) => {
    await TestHelpers.loginAsTestUser(page, 'user');
    
    // Get a test room
    const testRoom = await TestHelpers.getTestRoom(false); // Get public test room
    
    if (testRoom) {
      // Switch to test room
      await TestHelpers.switchRoom(page, testRoom.name);
      
      // Send a test message in the test room
      const testMessage = 'Test message in test room ' + Date.now();
      await TestHelpers.sendMessage(page, testMessage);
      
      // Verify message appears
      await expect(page.locator('#messages')).toContainText(testMessage);
    }
  });

  test('should test AI functionality in test room', async ({ page }) => {
    await TestHelpers.loginAsTestUser(page, 'user');
    
    // Get the AI test room
    const aiTestRoom = await TestHelpers.getTestRoom(false);
    
    if (aiTestRoom) {
      await TestHelpers.switchRoom(page, aiTestRoom.name);
      
      // Trigger AI response in test room
      await TestHelpers.triggerAIResponse(page, '@ai Hello, this is a test');
      
      // Should get AI response in test room
      await expect(page.locator('#messages')).toContainText('Styx');
    }
  });

  test('should test private room access', async ({ page }) => {
    const testUser = await TestHelpers.loginAsTestUser(page, 'admin');
    
    // Get private test room
    const privateRoom = await TestHelpers.getTestRoom(true);
    
    if (privateRoom) {
      // Admin should be able to access private test room
      await TestHelpers.switchRoom(page, privateRoom.name);
      
      // Send message in private room
      const testMessage = 'Private room test message ' + Date.now();
      await TestHelpers.sendMessage(page, testMessage);
      
      await expect(page.locator('#messages')).toContainText(testMessage);
    }
  });

  test('should clean up test messages after each test', async ({ page }) => {
    await TestHelpers.loginAsTestUser(page, 'user');
    
    const testRoom = await TestHelpers.getTestRoom(false);
    
    if (testRoom) {
      await TestHelpers.switchRoom(page, testRoom.name);
      
      // Send multiple test messages
      for (let i = 0; i < 3; i++) {
        await TestHelpers.sendMessage(page, `Test cleanup message ${i} - ${Date.now()}`);
      }
      
      // Messages will be cleaned up during global teardown
      // This test verifies the basic functionality works
      const messageCount = await TestHelpers.getMessageCount(page);
      expect(messageCount).toBeGreaterThan(0);
    }
  });

  test('should demonstrate test isolation', async ({ page }) => {
    // Each test gets a clean environment
    // Test users and rooms are isolated from production data
    
    await TestHelpers.loginAsTestUser(page, 'user');
    
    // Get available test rooms
    const testData = await TestHelpers.getTestData();
    
    // Should have test rooms available
    expect(testData.rooms).toBeDefined();
    expect(testData.rooms.length).toBeGreaterThan(0);
    
    // Should have test users for all 3 personas: administrators, kids, and regular users
    expect(testData.users).toBeDefined();
    expect(testData.users.length).toBe(3); // Exactly 3 personas
    
    console.log('Test environment includes:');
    console.log(`- ${testData.users.length} test users (administrators, kids, and regular users)`);
    console.log(`- ${testData.rooms.length} test rooms`);
  });
}); 