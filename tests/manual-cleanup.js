#!/usr/bin/env node

/**
 * Manual cleanup script for test environment
 * Can be run independently if global teardown fails
 */

const globalTeardown = require('./global-teardown');

// Mock config object for the teardown function
const mockConfig = {
  projects: [{
    use: {
      baseURL: 'https://localhost:3443'
    }
  }]
};

console.log('🧹 Running manual cleanup...');

globalTeardown(mockConfig)
  .then(() => {
    console.log('✅ Manual cleanup completed successfully');
    process.exit(0);
  })
  .catch((error) => {
    console.error('❌ Manual cleanup failed:', error);
    process.exit(1);
  }); 