import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ThemisMark from '../components/ThemisMark';

export default function LoginPage() {
  const { login }  = useAuth();
  const navigate   = useNavigate();
  const [form, setForm]       = useState({ username: '', password: '' });
  const [error, setError]     = useState('');
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }));
    setError('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.username || !form.password) { setError('Both fields are required.'); return; }
    setLoading(true);
    try {
      await login(form.username, form.password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(
        err.response?.data?.detail
        || err.response?.data?.non_field_errors?.[0]
        || 'Invalid credentials.'
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-root">
      <div className="auth-card">
        {/* Mark */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
          <ThemisMark size={28} color="var(--accent)" thinking={loading} />
          <span className="auth-wordmark" style={{ marginBottom: 0 }}>Themis</span>
        </div>

        <p className="auth-headline">Sign in</p>
        <p className="auth-sub">Access your compliance dashboard</p>

        {error && <div className="alert alert-error" style={{ marginBottom: 20 }}>{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label className="form-label" htmlFor="username">Username</label>
            <input
              id="username" name="username" type="text"
              className={`form-input${error ? ' is-error' : ''}`}
              placeholder="username"
              value={form.username}
              onChange={handleChange}
              autoComplete="username"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <input
              id="password" name="password" type="password"
              className={`form-input${error ? ' is-error' : ''}`}
              placeholder="••••••••"
              value={form.password}
              onChange={handleChange}
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full btn-lg"
            disabled={loading}
            style={{ marginTop: 4 }}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="auth-footer">
          No account? <Link to="/register">Register</Link>
        </div>
      </div>
    </div>
  );
}
