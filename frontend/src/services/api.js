import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';

// ── Axios instance ────────────────────────────────────────────────
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: attach Bearer token ──────────────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ── Response interceptor: silent token refresh on 401 ────────────
let _refreshing = false;
let _failedQueue = [];

function processQueue(error, token = null) {
  _failedQueue.forEach(({ resolve, reject }) =>
    error ? reject(error) : resolve(token)
  );
  _failedQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    if (_refreshing) {
      return new Promise((resolve, reject) => {
        _failedQueue.push({ resolve, reject });
      })
        .then((token) => {
          original.headers.Authorization = `Bearer ${token}`;
          return api(original);
        })
        .catch((err) => Promise.reject(err));
    }

    original._retry = true;
    _refreshing = true;

    const refresh = localStorage.getItem('refresh_token');
    if (!refresh) {
      _refreshing = false;
      window.location.href = '/login';
      return Promise.reject(error);
    }

    try {
      const { data } = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
        refresh,
      });
      localStorage.setItem('access_token', data.access);
      api.defaults.headers.common.Authorization = `Bearer ${data.access}`;
      processQueue(null, data.access);
      original.headers.Authorization = `Bearer ${data.access}`;
      return api(original);
    } catch (refreshError) {
      processQueue(refreshError, null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
      return Promise.reject(refreshError);
    } finally {
      _refreshing = false;
    }
  },
);

// ── Auth API ──────────────────────────────────────────────────────
export const authAPI = {
  login:    (username, password) =>
    api.post('/auth/login/', { username, password }),
  register: (data) =>
    api.post('/auth/register/', data),
  profile:  () =>
    api.get('/auth/profile/'),
  refresh:  (refresh) =>
    api.post('/auth/refresh/', { refresh }),
};

// ── Policies API ──────────────────────────────────────────────────
export const policiesAPI = {
  list:   ()         => api.get('/policies/'),
  detail: (id)       => api.get(`/policies/${id}/`),
  upload: (formData) =>
    api.post('/policies/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  delete: (id)       => api.delete(`/policies/${id}/`),
};

// ── Compliance API ────────────────────────────────────────────────
export const complianceAPI = {
  triggerScan:      (policyId)   => api.post('/compliance/scan/', { policy_id: policyId }),
  getReports:       ()           => api.get('/compliance/reports/'),
  getReport:        (reportId)   => api.get(`/compliance/reports/${reportId}/`),
  whatIfCheck:      (clauseText) => api.post('/compliance/what-if/', { clause_text: clauseText }),
  getDashboard:     ()           => api.get('/compliance/dashboard/'),
  resolveFlag:      (flagId)     => api.patch(`/compliance/flags/${flagId}/resolve/`),
  submitFeedback:   (flagId, data) => api.patch(`/compliance/flags/${flagId}/feedback/`, data),
};

// ── Laws API ──────────────────────────────────────────────────────
export const lawsAPI = {
  list:   ()    => api.get('/laws/'),
  detail: (id)  => api.get(`/laws/${id}/`),
};

// ── Reports / PDF ─────────────────────────────────────────────────
export const reportsAPI = {
  downloadPdf: (reportId) =>
    api.get(`/compliance/reports/${reportId}/pdf/`, { responseType: 'blob' }),
};

export default api;
