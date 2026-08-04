import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import PrivateRoute from './components/PrivateRoute';
import Layout from './components/Layout';

import LoginPage    from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import UploadPage   from './pages/UploadPage';
import ReportPage   from './pages/ReportPage';
import WhatIfPage   from './pages/WhatIfPage';
import ScanHistoryPage from './pages/ScanHistoryPage';
import LawDatabasePage from './pages/LawDatabasePage';

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public */}
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected — all wrapped in Layout */}
        <Route
          path="/dashboard"
          element={
            <PrivateRoute>
              <Layout><DashboardPage /></Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/upload"
          element={
            <PrivateRoute>
              <Layout><UploadPage /></Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/history"
          element={
            <PrivateRoute>
              <Layout><ScanHistoryPage /></Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/reports"
          element={
            <PrivateRoute>
              <Layout><ScanHistoryPage /></Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/reports/:id"
          element={
            <PrivateRoute>
              <Layout><ReportPage /></Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/what-if"
          element={
            <PrivateRoute>
              <Layout><WhatIfPage /></Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/laws"
          element={
            <PrivateRoute>
              <Layout><LawDatabasePage /></Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/law"
          element={
            <PrivateRoute>
              <Layout><LawDatabasePage /></Layout>
            </PrivateRoute>
          }
        />

        {/* Catch-all */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  );
}
