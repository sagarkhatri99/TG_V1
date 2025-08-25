import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;

export const endpoints = {
  health: '/health',
  stats: '/stats',
  
  accounts: {
    list: '/api/accounts/list',
    create: '/api/accounts/create',
    sendCode: (id: number) => `/api/accounts/${id}/send-code`,
    verify: (id: number) => `/api/accounts/${id}/verify`,
    test: (id: number) => `/api/accounts/${id}/test`,
    pause: (id: number) => `/api/accounts/${id}/pause`,
    resume: (id: number) => `/api/accounts/${id}/resume`,
    stats: (id: number) => `/api/accounts/${id}/stats`,
  },
  
  scraping: {
    startAuth: '/api/scrape-users/start-auth',
    verifyScrape: '/api/scrape-users/verify-scrape',
    download: '/api/scrape-users/download',
  },
  
  monitoring: {
    startAuth: '/api/group-monitor/start-auth',
    verifyMonitor: '/api/group-monitor/verify-monitor',
    download: '/api/group-monitor/download',
  },
  
  massDM: {
    bot: '/api/mass-dm-bot/',
    account: {
      startAuth: '/api/mass-dm-account/start-auth',
      send: '/api/mass-dm-account/send',
    },
  },
  
  autoPromo: {
    startAuth: '/api/auto_promo/start-auth',
    start: '/api/auto_promo/start',
  },
};
