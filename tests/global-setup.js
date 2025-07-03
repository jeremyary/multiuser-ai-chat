const { request } = require('@playwright/test');
const fs = require('fs').promises;
const path = require('path');

/**
 * Global setup for test suite
 * Creates test users and rooms before tests run
 */
async function globalSetup(config) {
  console.log('🚀 Setting up test environment...');
  
  const baseURL = config?.projects?.[0]?.use?.baseURL || 'https://localhost:3443';
  const apiContext = await request.newContext({
    baseURL: baseURL,
    ignoreHTTPSErrors: true
  });

  const testData = {
    users: [],
    rooms: [],
    adminToken: null
  };

  try {
    // 1. Login as admin to get token for API calls
    console.log('🔑 Authenticating as admin...');
    const loginResponse = await apiContext.post('/auth/login', {
      data: {
        username: 'admin',
        password: 'admin123!'
      }
    });
    
    if (!loginResponse.ok()) {
      throw new Error(`Admin login failed: ${loginResponse.status()}`);
    }
    
    const loginData = await loginResponse.json();
    testData.adminToken = loginData.access_token;
    
    // 2. Create test users with different personas
    console.log('👥 Creating test users...');
    const testUsers = [
      {
        username: 'test_user_regular',
        password: 'testpass123!',
        full_name: 'Test Regular User',
        role: 'user',
        is_kid_account: false,
        avatar_color: '#3498db'
      },
      {
        username: 'test_user_kid',
        password: 'testpass123!',
        full_name: 'Test Kid User',
        role: 'user',
        is_kid_account: true,
        avatar_color: '#f39c12'
      },
      {
        username: 'test_admin_secondary',
        password: 'testpass123!',
        full_name: 'Test Admin User',
        role: 'admin',
        is_kid_account: false,
        avatar_color: '#e74c3c'
      }
    ];

    for (const userData of testUsers) {
      try {
        const createUserResponse = await apiContext.post('/admin/users', {
          headers: {
            'Authorization': `Bearer ${testData.adminToken}`
          },
          data: userData
        });
        
        if (createUserResponse.ok()) {
          const user = await createUserResponse.json();
          testData.users.push({
            id: user.id,
            username: userData.username,
            password: userData.password,
            role: userData.role,
            is_kid_account: userData.is_kid_account
          });
          console.log(`  ✅ Created user: ${userData.username} (${userData.role})`);
        } else {
          // User creation failed, log the error and try to find if it exists
          console.log(`  ❌ User creation failed for ${userData.username}: ${createUserResponse.status()}`);
          try {
            const errorBody = await createUserResponse.json();
            console.log(`  📋 Error details: ${JSON.stringify(errorBody)}`);
          } catch (e) {
            console.log(`  📋 Error details: Unable to parse error response`);
          }
          
          // Try to find existing user
          console.log(`  🔍 Attempting to retrieve existing user...`);
          try {
            const getUsersResponse = await apiContext.get('/users', {
              headers: {
                'Authorization': `Bearer ${testData.adminToken}`
              }
            });
            
            if (getUsersResponse.ok()) {
              const usersData = await getUsersResponse.json();
              const existingUser = usersData.users.find(u => u.username === userData.username);
              if (existingUser) {
                testData.users.push({
                  id: existingUser.id,
                  username: userData.username,
                  password: userData.password,
                  role: userData.role,
                  is_kid_account: userData.is_kid_account
                });
                console.log(`  ✅ Found existing user: ${userData.username} (${userData.role})`);
              } else {
                console.log(`  ❌ User ${userData.username} not found in user list`);
              }
            } else {
              console.log(`  ❌ Failed to retrieve user list: ${getUsersResponse.status()}`);
            }
          } catch (error) {
            console.log(`  ❌ Error retrieving user ${userData.username}: ${error.message}`);
          }
        }
      } catch (error) {
        console.log(`  ⚠️  Failed to create user ${userData.username}: ${error.message}`);
      }
    }

    // 3. Create test rooms
    console.log('🏠 Creating test rooms...');
    const testRooms = [
      {
        room_name: 'test_public_room',
        description: 'Public test room for automated tests',
        is_private: false,
        ai_system_prompt: 'You are a helpful assistant in a test environment.',
        voice_readback_enabled: false
      },
      {
        room_name: 'test_private_room',
        description: 'Private test room for automated tests',
        is_private: true,
        ai_system_prompt: 'You are a helpful assistant for private conversations.',
        voice_readback_enabled: false
      },
      {
        room_name: 'test_ai_room',
        description: 'Test room with custom AI configuration',
        is_private: false,
        ai_system_prompt: 'You are a coding assistant specialized in JavaScript and Python.',
        voice_readback_enabled: true
      }
    ];

    for (const roomData of testRooms) {
      try {
        const createRoomResponse = await apiContext.post('/rooms', {
          headers: {
            'Authorization': `Bearer ${testData.adminToken}`
          },
          data: roomData
        });
        
        if (createRoomResponse.ok()) {
          const room = await createRoomResponse.json();
          testData.rooms.push({
            id: room.room_id,
            name: roomData.room_name,
            is_private: roomData.is_private
          });
          console.log(`  ✅ Created room: ${roomData.room_name}`);
        } else {
          console.log(`  ⚠️  Room ${roomData.room_name} might already exist, skipping...`);
        }
      } catch (error) {
        console.log(`  ⚠️  Failed to create room ${roomData.room_name}: ${error.message}`);
      }
    }

    // 4. Save test data to file for use in tests and teardown
    const testDataPath = path.join(__dirname, 'test-data.json');
    await fs.writeFile(testDataPath, JSON.stringify(testData, null, 2));
    console.log(`💾 Test data saved to: ${testDataPath}`);

    // 5. Clear messages from test rooms to ensure clean state
    console.log('🧹 Clearing messages from test rooms...');
    for (const room of testData.rooms) {
      try {
        const clearResponse = await apiContext.delete(`/rooms/${room.id}/messages`, {
          headers: {
            'Authorization': `Bearer ${testData.adminToken}`
          }
        });
        
        if (clearResponse.ok()) {
          console.log(`  ✅ Cleared messages from room: ${room.name}`);
        } else {
          console.log(`  ⚠️  Could not clear messages from room ${room.name}: ${clearResponse.status()}`);
        }
      } catch (error) {
        console.log(`  ⚠️  Error clearing messages from room ${room.name}: ${error.message}`);
      }
    }

    console.log('✅ Test environment setup complete!');
    console.log(`   - Created ${testData.users.length} test users`);
    console.log(`   - Created ${testData.rooms.length} test rooms`);

  } catch (error) {
    console.error('❌ Failed to setup test environment:', error);
    throw error;
  } finally {
    await apiContext.dispose();
  }
}

module.exports = globalSetup;

// Allow running as standalone script
if (require.main === module) {
  const mockConfig = {
    projects: [{
      use: {
        baseURL: 'https://localhost:3443'
      }
    }]
  };
  
  globalSetup(mockConfig)
    .then(() => {
      console.log('✅ Standalone setup completed successfully');
      process.exit(0);
    })
    .catch((error) => {
      console.error('❌ Standalone setup failed:', error);
      process.exit(1);
    });
} 