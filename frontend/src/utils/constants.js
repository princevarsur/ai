// API base URL
export const API_BASE_URL = 'http://localhost:8000/api';

// Route paths
export const ROUTES = {
  HOME:       '/',
  LOGIN:      '/login',
  REGISTER:   '/register',
  DASHBOARD:  '/dashboard',
  UPLOAD:     '/upload',
  REPORTS:    '/reports',
  REPORT:     '/reports/:id',
  WHAT_IF:    '/what-if',
  LAWS:       '/laws',
};

// Severity / status colours (matches index.css badge classes)
export const STATUS_CONFIG = {
  conflict: { label: 'Conflict',  badgeClass: 'badge-conflict', color: 'var(--danger)'  },
  missing:  { label: 'Missing',   badgeClass: 'badge-missing',  color: 'var(--warning)' },
  gap:      { label: 'Gap',       badgeClass: 'badge-gap',      color: 'var(--accent)'  },
  compliant:{ label: 'Compliant', badgeClass: 'badge-ok',       color: 'var(--success)' },
};

// Severity score thresholds
export const SEVERITY = {
  CRITICAL: { min: 80, label: 'Critical', color: 'var(--danger)'  },
  HIGH:     { min: 60, label: 'High',     color: 'var(--warning)' },
  MEDIUM:   { min: 40, label: 'Medium',   color: 'var(--accent)'  },
  LOW:      { min: 0,  label: 'Low',      color: 'var(--success)' },
};

// Law category labels
export const CATEGORY_LABELS = {
  maternity:       'Maternity Benefit Act',
  posh:            'POSH Act',
  dpdp:            'DPDP Act',
  epf:             'EPF / Labour Codes',
  gratuity:        'Payment of Gratuity',
  companies_act:   'Companies Act',
};

// Sidebar nav items
export const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard',       icon: 'grid' },
  { path: '/upload',    label: 'Upload Policy',   icon: 'upload' },
  { path: '/reports',   label: 'Scan History',    icon: 'file-text' },
  { path: '/what-if',   label: 'What-If Checker', icon: 'search' },
  { path: '/laws',      label: 'Law Database',    icon: 'book' },
];
