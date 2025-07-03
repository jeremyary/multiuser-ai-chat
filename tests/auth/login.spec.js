const { test, expect } = require('@playwright/test');

test.describe('Authentication Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display login form on initial load', async ({ page }) => {
    await expect(page.locator('#loginContainer')).toBeVisible();
    await expect(page.locator('h2')).toContainText('Login');
    await expect(page.locator('#username')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.locator('button:has-text("Login")')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.fill('#username', 'invalid_user');
    await page.fill('#password', 'wrong_password');
    await page.click('button:has-text("Login")');
    
    await expect(page.locator('#errorMessage')).toBeVisible();
    await expect(page.locator('#errorMessage')).toContainText('Login failed');
  });

  test('should show error for empty fields', async ({ page }) => {
    await page.click('button:has-text("Login")');
    
    // HTML5 validation should prevent form submission
    await expect(page.locator('#loginContainer')).toBeVisible();
  });

  test('should successfully login with valid credentials', async ({ page }) => {
    // Use a test user that should exist in your system
    await page.fill('#username', 'admin');
    await page.fill('#password', 'admin123!');
    await page.click('button:has-text("Login")');
    
    // Wait for successful login
    await expect(page.locator('#chatContainer')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#loginContainer')).not.toBeVisible();
    
    // Verify user is logged in
    await expect(page.locator('#currentUserName')).toContainText('admin');
    await expect(page.locator('#headerActions')).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.fill('#username', 'admin');
    await page.fill('#password', 'admin123!');
    await page.click('button:has-text("Login")');
    
    await expect(page.locator('#chatContainer')).toBeVisible({ timeout: 10000 });
    
    // Logout
    await page.click('button:has-text("Logout")');
    
    // Verify logout
    await expect(page.locator('#loginContainer')).toBeVisible();
    await expect(page.locator('#chatContainer')).not.toBeVisible();
    await expect(page.locator('#headerActions')).not.toBeVisible();
  });

  test('should handle Enter key on password field', async ({ page }) => {
    await page.fill('#username', 'admin');
    await page.fill('#password', 'admin123!');
    await page.press('#password', 'Enter');
    
    // Should trigger login
    await expect(page.locator('#chatContainer')).toBeVisible({ timeout: 10000 });
  });

  test('should show admin features for admin user', async ({ page }) => {
    await page.fill('#username', 'admin');
    await page.fill('#password', 'admin123!');
    await page.click('button:has-text("Login")');
    
    await expect(page.locator('#chatContainer')).toBeVisible({ timeout: 10000 });
    
    // Admin should see user management button
    await expect(page.locator('#userMgmtBtn')).toBeVisible();
  });

  test('should maintain session after page refresh', async ({ page }) => {
    // Login first
    await page.fill('#username', 'admin');
    await page.fill('#password', 'admin123!');
    await page.click('button:has-text("Login")');
    
    await expect(page.locator('#chatContainer')).toBeVisible({ timeout: 10000 });
    
    // Refresh the page
    await page.reload();
    
    // Should still be logged in (if your app supports this)
    // Note: This depends on your JWT token storage implementation
    await expect(page.locator('#loginContainer')).toBeVisible();
  });

  test('should clear form fields after logout', async ({ page }) => {
    await page.fill('#username', 'admin');
    await page.fill('#password', 'admin123!');
    await page.click('button:has-text("Login")');
    
    await expect(page.locator('#chatContainer')).toBeVisible({ timeout: 10000 });
    
    await page.click('button:has-text("Logout")');
    
    // Form fields should be cleared
    await expect(page.locator('#username')).toHaveValue('');
    await expect(page.locator('#password')).toHaveValue('');
    await expect(page.locator('#errorMessage')).toHaveText('');
  });
}); 