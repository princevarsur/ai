import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function PrivateRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', color: 'var(--text-tertiary)', flexDirection: 'column', gap: 12,
      }}>
        <span className="spinner" style={{ width: 24, height: 24 }} />
        <span style={{ fontSize: '0.875rem' }}>Loading...</span>
      </div>
    );
  }

  return isAuthenticated ? children : <Navigate to="/login" replace />;
}
