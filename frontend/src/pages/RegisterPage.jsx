import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import ThemisMark from '../components/ThemisMark';

const ROLES = [
  { value: 'compliance_officer', label: 'Compliance Officer' },
  { value: 'legal_counsel',      label: 'Legal Counsel'      },
  { value: 'hr_manager',         label: 'HR Manager'         },
  { value: 'admin',              label: 'Administrator'      },
];

export default function RegisterPage() {
  const { login }  = useAuth();
  const navigate   = useNavigate();

  const [form, setForm] = useState({
    username: '', email: '', password: '', password_confirm: '',
    role: 'compliance_officer', company_name: '',
  });
  const [errors, setErrors]     = useState({});
  const [apiError, setApiError] = useState('');
  const [loading, setLoading]   = useState(false);

  function handleChange(e) {
    setForm(f => ({ ...f, [e.target.name]: e.target.value }));
    setErrors(p => ({ ...p, [e.target.name]: '' }));
    setApiError('');
  }

  function validate() {
    const e = {};
    if (!form.username)     e.username     = 'Required';
    if (!form.email)        e.email        = 'Required';
    if (!form.company_name) e.company_name = 'Required';
    if (!form.password)              e.password = 'Required';
    else if (form.password.length < 8)    e.password = 'Minimum 8 characters';
    if (form.password !== form.password_confirm) e.password_confirm = 'Passwords do not match';
    return e;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setLoading(true);
    try {
      await authAPI.register(form);
      await login(form.username, form.password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      const data = err.response?.data;
      if (data && typeof data === 'object') {
        const mapped = {};
        for (const [k, v] of Object.entries(data)) {
          mapped[k] = Array.isArray(v) ? v[0] : v;
        }
        setErrors(mapped);
      } else {
        setApiError('Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  function field(name, label, type = 'text', placeholder = '') {
    return (
      <div className="form-group">
        <label className="form-label" htmlFor={name}>{label}</label>
        <input
          id={name} name={name} type={type}
          className={`form-input${errors[name] ? ' is-error' : ''}`}
          placeholder={placeholder}
          value={form[name]}
          onChange={handleChange}
          autoComplete={type === 'password' ? 'new-password' : name}
        />
        {errors[name] && <span className="form-error">{errors[name]}</span>}
      </div>
    );
  }

  return (
    <div className="auth-root">
      <div className="auth-card" style={{ maxWidth: 460 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
          <ThemisMark size={28} color="var(--accent)" thinking={loading} />
          <span className="auth-wordmark" style={{ marginBottom: 0 }}>Themis</span>
        </div>

        <p className="auth-headline">Create account</p>
        <p className="auth-sub">Register your organisation on the compliance platform</p>

        {apiError && <div className="alert alert-error" style={{ marginBottom: 20 }}>{apiError}</div>}

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            {field('username',     'Username',  'text', 'john_doe')}
            {field('company_name', 'Company',   'text', 'Acme Pvt. Ltd.')}
          </div>

          {field('email', 'Email address', 'email', 'john@company.com')}

          <div className="form-group">
            <label className="form-label" htmlFor="role">Role</label>
            <select
              id="role" name="role"
              className="form-input form-select"
              value={form.role}
              onChange={handleChange}
            >
              {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            {field('password',         'Password',         'password', '••••••••')}
            {field('password_confirm', 'Confirm password', 'password', '••••••••')}
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-full btn-lg"
            disabled={loading}
            style={{ marginTop: 4 }}
          >
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <div className="auth-footer">
          Already registered? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
