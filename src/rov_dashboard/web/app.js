import { DashboardApp } from './js/dashboard-app.js';

window.addEventListener('DOMContentLoaded', async () => {
  const app = new DashboardApp();

  try {
    await app.initialize();
  } catch (error) {
    console.error('Dashboard initialization failed:', error);
  }
});
