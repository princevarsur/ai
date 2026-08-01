import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await login(username, password);
    
    if (result.success) {
      navigate('/dashboard');
    } else {
      setError(result.error);
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-primary)',
      padding: '2rem',
    }}>
      <div style={{
        width: '100%',
        maxWidth: '420px',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <h1 style={{
            fontSize: '2.5rem',
            fontWeight: 700,
            color: 'var(--accent-primary)',
            margin: 0,
          }}>
            THEMIS
          </h1>
          <p style={{
            fontSize: '0.875rem',
            color: 'var(--text-tertiary)',
            marginTop: '0.5rem',
          }}>
            Legal Compliance AI Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="card" style={{
          padding: '2rem',
        }}>
          <h2 style={{
            fontSize: '1.5rem',
            fontWeight: 600,
            marginBottom: '1.5rem',
            textAlign: 'center',
          }}>
            Sign In
          </h2>

          <form onSubmit={handleSubmit}>
            {error && (
              <div style={{
                padding: '0.75rem',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid var(--error)',
                borderRadius: '8px',
                color: 'var(--error)',
                fontSize: '0.875rem',
                marginBottom: '1rem',
              }}>
                {error}
              </div>
            )}

            <div style={{ marginBottom: '1rem' }}>
              <label style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: 500,
                marginBottom: '0.5rem',
                color: 'var(--text-secondary)',
              }}>
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
                autoFocus
              />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: 500,
                marginBottom: '0.5rem',
                color: 'var(--text-secondary)',
              }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.75rem',
                background: loading ? 'var(--bg-tertiary)' : 'var(--accent-primary)',
                color: 'var(--text-primary)',
                border: 'none',
                borderRadius: '8px',
                fontSize: '0.9375rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
              }}
            >
              {loading ? (
                <>
                  <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }}></div>
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div style={{
            marginTop: '1.5rem',
            textAlign: 'center',
            fontSize: '0.875rem',
            color: 'var(--text-secondary)',
          }}>
            Don't have an account?{' '}
            <Link
              to="/register"
              style={{
                color: 'var(--accent-primary)',
                fontWeight: 500,
              }}
            >
              Sign up
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
