import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - attach token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle 401 and refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
            refresh: refreshToken,
          });
          localStorage.setItem('access_token', data.access);
          originalRequest.headers.Authorization = `Bearer ${data.access}`;
          return api(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      } else {
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (username, password) =>
    api.post('/auth/login/', { username, password }),
  
  register: (data) =>
    api.post('/auth/register/', data),
  
  refresh: (refreshToken) =>
    api.post('/auth/refresh/', { refresh: refreshToken }),
};

// Policies API
export const policiesAPI = {
  list: () => api.get('/policies/'),
  
  detail: (id) => api.get(`/policies/${id}/`),
  
  upload: (formData) =>
    api.post('/policies/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
};

// Compliance API
export const complianceAPI = {
  triggerScan: (policyId) =>
    api.post('/compliance/scan/', { policy_id: policyId }),
  
  getReport: (reportId) =>
    api.get(`/compliance/reports/${reportId}/`),
  
  getReports: () =>
    api.get('/compliance/reports/'),
  
  whatIfCheck: (clauseText) =>
    api.post('/compliance/what-if/', { clause_text: clauseText }),
  
  getDashboard: () =>
    api.get('/compliance/dashboard/'),
  
  getAccuracyMetrics: () =>
    api.get('/compliance/accuracy/'),
};

// Laws API
export const lawsAPI = {
  list: () => api.get('/laws/'),
  
  detail: (id) => api.get(`/laws/${id}/`),
};

// Reports API
export const reportsAPI = {
  downloadPdf: (reportId) =>
    api.get(`/reports/${reportId}/pdf/`, {
      responseType: 'blob',
    }),
};

export default api;
