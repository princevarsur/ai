export const API_BASE_URL = 'http://localhost:8000/api';

export const RISK_LEVELS = {
  CRITICAL: { label: 'Critical', color: 'var(--risk-critical)' },
  HIGH: { label: 'High', color: 'var(--risk-high)' },
  MEDIUM: { label: 'Medium', color: 'var(--risk-medium)' },
  LOW: { label: 'Low', color: 'var(--risk-low)' },
  COMPLIANT: { label: 'Compliant', color: 'var(--risk-compliant)' },
};

export const CATEGORY_LABELS = {
  data_privacy: 'Data Privacy',
  consumer_protection: 'Consumer Protection',
  labor_rights: 'Labor Rights',
  intellectual_property: 'Intellectual Property',
  contract_terms: 'Contract Terms',
  regulatory_compliance: 'Regulatory Compliance',
};

export const API_ENDPOINTS = {
  // Auth
  LOGIN: '/auth/login/',
  REGISTER: '/auth/register/',
  REFRESH: '/auth/refresh/',
  
  // Policies
  POLICIES: '/policies/',
  POLICY_DETAIL: (id) => `/policies/${id}/`,
  POLICY_UPLOAD: '/policies/upload/',
  
  // Compliance
  SCAN_TRIGGER: '/compliance/scan/',
  REPORTS: '/compliance/reports/',
  REPORT_DETAIL: (id) => `/compliance/reports/${id}/`,
  WHAT_IF: '/compliance/what-if/',
  DASHBOARD: '/compliance/dashboard/',
  ACCURACY_METRICS: '/compliance/accuracy/',
  
  // Laws
  LAWS: '/laws/',
  LAW_DETAIL: (id) => `/laws/${id}/`,
};
