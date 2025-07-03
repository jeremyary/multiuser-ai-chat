const { request } = require('@playwright/test');
const fs = require('fs').promises;
const path = require('path');
const { spawn } = require('child_process');

/**
 * Global teardown for test suite
 * Uses the comprehensive cleanup script to clean up test environment
 */
async function globalTeardown(config) {
  console.log('🧹 Cleaning up test environment...');
  
  try {
    // 1. Try to clean up using the comprehensive cleanup script
    console.log('🧹 Running comprehensive cleanup script...');
    await runCleanupScript();
    
    // 2. Clean up test data file
    const testDataPath = path.join(__dirname, 'test-data.json');
    try {
      await fs.unlink(testDataPath);
      console.log('💾 Test data file cleaned up');
    } catch (error) {
      console.log('⚠️  Test data file already cleaned up or not found');
    }

    console.log('✅ Test environment cleanup complete!');

  } catch (error) {
    console.error('❌ Failed to cleanup test environment:', error.message);
    
    // Fallback to manual cleanup if comprehensive script fails
    console.log('🔄 Attempting fallback cleanup...');
    await fallbackCleanup(config);
  }
}

/**
 * Run the comprehensive cleanup script
 */
async function runCleanupScript() {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(__dirname, '..', 'cleanup_all.py');
    const cleanup = spawn('python', [scriptPath], {
      stdio: 'pipe',
      cwd: path.join(__dirname, '..')
    });

    let output = '';
    let error = '';

    cleanup.stdout.on('data', (data) => {
      output += data.toString();
    });

    cleanup.stderr.on('data', (data) => {
      error += data.toString();
    });

    cleanup.on('close', (code) => {
      if (code === 0) {
        console.log('✅ Cleanup script completed successfully');
        if (output.trim()) {
          console.log('📋 Cleanup output:', output.trim());
        }
        resolve();
      } else {
        console.error('❌ Cleanup script failed with exit code:', code);
        if (error.trim()) {
          console.error('Error details:', error.trim());
        }
        reject(new Error(`Cleanup script failed with exit code ${code}`));
      }
    });

    cleanup.on('error', (err) => {
      console.error('❌ Failed to spawn cleanup script:', err.message);
      reject(err);
    });
  });
}

/**
 * Fallback cleanup using API calls (if comprehensive script fails)
 */
async function fallbackCleanup(config) {
  console.log('🔄 Running fallback API-based cleanup...');
  
  const baseURL = config.projects[0]?.use?.baseURL || 'https://localhost:3443';
  const apiContext = await request.newContext({
    baseURL: baseURL,
    ignoreHTTPSErrors: true
  });

  try {
    // 1. Load test data from setup
    const testDataPath = path.join(__dirname, 'test-data.json');
    let testData;
    
    try {
      const testDataContent = await fs.readFile(testDataPath, 'utf-8');
      testData = JSON.parse(testDataContent);
    } catch (error) {
      console.log('⚠️  No test data file found, attempting to authenticate...');
      
      // Try to authenticate as admin
      const loginResponse = await apiContext.post('/auth/login', {
        data: {
          username: 'admin',
          password: 'admin123!'
        }
      });
      
      if (loginResponse.ok()) {
        const loginData = await loginResponse.json();
        testData = { adminToken: loginData.access_token };
      } else {
        console.error('❌ Failed to authenticate for fallback cleanup');
        return;
      }
    }

    // 2. Delete test rooms
    if (testData.rooms && testData.rooms.length > 0) {
      console.log('🏠 Deleting test rooms...');
      
      for (const room of testData.rooms) {
        try {
          const deleteRoomResponse = await apiContext.delete(`/rooms/${room.id}`, {
            headers: {
              'Authorization': `Bearer ${testData.adminToken}`
            }
          });
          
          if (deleteRoomResponse.ok()) {
            console.log(`  ✅ Deleted room: ${room.name}`);
          } else {
            console.log(`  ⚠️  Failed to delete room: ${room.name}`);
          }
        } catch (error) {
          console.log(`  ⚠️  Error deleting room ${room.name}: ${error.message}`);
        }
      }
    }

    // 3. Delete test users (soft delete via API)
    if (testData.users && testData.users.length > 0) {
      console.log('👥 Deleting test users...');
      
      for (const user of testData.users) {
        try {
          const deleteUserResponse = await apiContext.delete(`/admin/users/${user.id}`, {
            headers: {
              'Authorization': `Bearer ${testData.adminToken}`
            }
          });
          
          if (deleteUserResponse.ok()) {
            console.log(`  ✅ Deleted user: ${user.username}`);
          } else {
            console.log(`  ⚠️  Failed to delete user: ${user.username}`);
          }
        } catch (error) {
          console.log(`  ⚠️  Error deleting user ${user.username}: ${error.message}`);
        }
      }
    }

    console.log('✅ Fallback cleanup completed');

  } catch (error) {
    console.error('❌ Fallback cleanup failed:', error.message);
  } finally {
    await apiContext.dispose();
  }
}

module.exports = globalTeardown;

// Allow running as standalone script
if (require.main === module) {
  const mockConfig = {
    projects: [{
      use: {
        baseURL: 'https://localhost:3443'
      }
    }]
  };
  
  globalTeardown(mockConfig)
    .then(() => {
      console.log('✅ Standalone teardown completed successfully');
      process.exit(0);
    })
    .catch(error => {
      console.error('❌ Standalone teardown failed:', error);
      process.exit(1);
    });
} 