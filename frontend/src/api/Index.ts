import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;

export const endpoints = {
  health: '/health',
  stats: '/stats',
  me: {
    stats: '/api/me/stats',
  },

  accounts: {
    list: '/api/accounts/list',
    create: '/api/accounts/create',
    sendCode: (id: number) => `/api/accounts/${id}/send-code`,
    verify: (id: number) => `/api/accounts/${id}/verify`,
    test: (id: number) => `/api/accounts/${id}/test`,
    pause: (id: number) => `/api/accounts/${id}/pause`,
    resume: (id: number) => `/api/accounts/${id}/resume`,
    delete: (id: number) => `/api/accounts/${id}`,
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

  admin: {
    users: '/api/admin/users',
    stats: '/api/admin/stats',
    updateUser: (id: number) => `/api/admin/users/${id}`,
    deleteUser: (id: number) => `/api/admin/users/${id}`,
  },

  jobs: {
    list: '/api/jobs/list',
    create: '/api/jobs/create',
    cancel: (id: number) => `/api/jobs/${id}/cancel`,
    restart: (id: number) => `/api/jobs/${id}/restart`,
    delete: (id: number) => `/api/jobs/${id}`,
    download: (id: number) => `/api/jobs/${id}/download`,
  },

  healthMonitor: {
    overview: '/api/health/overview',
    account: (id: number) => `/api/health/account/${id}`,
    reset: (id: number) => `/api/health/reset/${id}`,
    alerts: '/api/health/alerts',
  },

  campaigns: {
    list: (status_filter?: string) => `/api/campaigns/?${status_filter ? `status_filter=${status_filter}` : ''}`,
    create: '/api/campaigns/',
    stats: '/api/campaigns/stats',
    get: (id: number) => `/api/campaigns/${id}`,
    update: (id: number) => `/api/campaigns/${id}`,
    delete: (id: number) => `/api/campaigns/${id}`,
    start: (id: number) => `/api/campaigns/${id}/start`,
    pause: (id: number) => `/api/campaigns/${id}/pause`,
    resume: (id: number) => `/api/campaigns/${id}/resume`,
    interactions: (id: number, status_filter?: string) => `/api/campaigns/${id}/interactions?${status_filter ? `status_filter=${status_filter}` : ''}`,
    logs: (id: number) => `/api/campaigns/${id}/logs`,
    accountSettings: (accountId: number) => `/api/accounts/${accountId}/operating-hours`,
  },
};
