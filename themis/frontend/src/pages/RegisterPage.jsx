import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const RegisterPage = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password2: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.password2) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    const result = await register({
      username: formData.username,
      email: formData.email,
      password: formData.password,
      password_confirm: formData.password2,
    });
    
    if (result.success) {
      navigate('/login', {
        state: { message: 'Registration successful! Please log in.' }
      });
    } else {
      if (typeof result.error === 'object') {
        const errors = Object.entries(result.error)
          .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`)
          .join('; ');
        setError(errors);
      } else {
        setError(result.error);
      }
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

        {/* Register Card */}
        <div className="card" style={{
          padding: '2rem',
        }}>
          <h2 style={{
            fontSize: '1.5rem',
            fontWeight: 600,
            marginBottom: '1.5rem',
            textAlign: 'center',
          }}>
            Create Account
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
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder="Choose a username"
                required
                autoFocus
              />
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: 500,
                marginBottom: '0.5rem',
                color: 'var(--text-secondary)',
              }}>
                Email
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="Enter your email"
                required
              />
            </div>

            <div style={{ marginBottom: '1rem' }}>
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
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Create a password (min 8 characters)"
                required
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
                Confirm Password
              </label>
              <input
                type="password"
                name="password2"
                value={formData.password2}
                onChange={handleChange}
                placeholder="Confirm your password"
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
                  Creating account...
                </>
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          <div style={{
            marginTop: '1.5rem',
            textAlign: 'center',
            fontSize: '0.875rem',
            color: 'var(--text-secondary)',
          }}>
            Already have an account?{' '}
            <Link
              to="/login"
              style={{
                color: 'var(--accent-primary)',
                fontWeight: 500,
              }}
            >
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
