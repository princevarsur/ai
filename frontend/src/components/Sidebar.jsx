import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { NAV_ITEMS } from '../utils/constants';
import ThemisMark from './ThemisMark';

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  // ── Sidebar colour palette (calm slate & charcoal) ──────────
  const C = {
    bg:               '#16181A',   // deep charcoal base
    border:           '#26292E',   // subtle hairline divider
    labelText:        '#606672',   // small-caps label
    navText:          '#9EA4B0',   // idle nav link
    navHoverBg:       '#202328',   // hover row
    navHoverText:     '#E2E8F0',
    navActiveBg:      '#282C34',   // calm, neutral slate fill
    navActiveBorder:  '#3E4452',   // subtle slate border outline
    navActiveText:    '#F8FAFC',   // crisp text
    userBoxBg:        '#1F2227',   // outlined account box fill
    userBoxBorder:    '#2D3139',   // account box outline
    userNameText:     '#E2E8F0',
    userRoleText:     '#606672',
    signOutBg:        '#202328',   // filled sign-out box
    signOutBorder:    '#2D3139',
    signOutText:      '#9EA4B0',
    signOutHoverBg:   '#A33F3F1A',
    signOutHoverText: '#E57373',
    markColor:        '#94A3B8',   // neutral steel slate mark
    wordmarkText:     '#F8FAFC',
    subtitleText:     '#606672',
  };

  return (
    <aside style={{
      width: 'var(--sidebar-w)',
      minHeight: '100vh',
      background: C.bg,
      borderRight: `1px solid ${C.border}`,
      display: 'flex',
      flexDirection: 'column',
      position: 'fixed',
      left: 0, top: 0, bottom: 0,
      zIndex: 100,
    }}>

      {/* ── Wordmark ───────────────────────────────────────────── */}
      <div style={{
        padding: '20px 18px 16px',
        borderBottom: `1px solid ${C.border}`,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}>
        <ThemisMark size={22} color={C.markColor} />
        <div>
          <div style={{
            fontFamily: "'IBM Plex Sans', sans-serif",
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: '0.10em',
            textTransform: 'uppercase',
            color: C.wordmarkText,
          }}>
            Themis
          </div>
          <div style={{ fontSize: 10, color: C.subtitleText, letterSpacing: '0.04em', marginTop: 1 }}>
            Compliance Engine
          </div>
        </div>
      </div>

      {/* ── Section label ─────────────────────────────────────── */}
      <div style={{ padding: '16px 18px 6px' }}>
        <span style={{
          fontSize: 10,
          fontWeight: 500,
          textTransform: 'uppercase',
          letterSpacing: '0.09em',
          color: C.labelText,
        }}>
          Navigation
        </span>
      </div>

      {/* ── Nav links ─────────────────────────────────────────── */}
      <nav style={{ flex: 1, padding: '0 10px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {NAV_ITEMS.map(({ path, label }) => (
          <NavLink
            key={path}
            to={path}
            style={({ isActive }) => ({
              display: 'block',
              padding: '8px 12px',
              borderRadius: 4,
              fontSize: 13,
              fontWeight: isActive ? 500 : 400,
              color: isActive ? C.navActiveText : C.navText,
              background: isActive ? C.navActiveBg : 'transparent',
              border: `1px solid ${isActive ? C.navActiveBorder : 'transparent'}`,
              textDecoration: 'none',
              transition: 'all 150ms ease-out',
            })}
            onMouseEnter={e => {
              if (!e.currentTarget.getAttribute('aria-current')) {
                e.currentTarget.style.background = C.navHoverBg;
                e.currentTarget.style.color = C.navHoverText;
              }
            }}
            onMouseLeave={e => {
              if (!e.currentTarget.getAttribute('aria-current')) {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = C.navText;
              }
            }}
          >
            {label}
          </NavLink>
        ))}
      </nav>

      {/* ── Bottom block ──────────────────────────────────────── */}
      <div style={{ padding: '10px 10px 12px', borderTop: `1px solid ${C.border}` }}>

        {/* Account box — outlined fill */}
        {user && (
          <div style={{
            padding: '10px 12px',
            marginBottom: 8,
            borderRadius: 5,
            background: C.userBoxBg,
            border: `1px solid ${C.userBoxBorder}`,
          }}>
            <div style={{
              fontSize: 13,
              fontWeight: 500,
              color: C.userNameText,
              lineHeight: 1.3,
            }}>
              {user.username}
            </div>
            <div style={{
              fontSize: 11,
              color: C.userRoleText,
              marginTop: 3,
              textTransform: 'capitalize',
            }}>
              {(user.company_name || user.role?.replace(/_/g, ' '))}
            </div>
          </div>
        )}

        {/* Sign out — filled box */}
        <button
          onClick={handleLogout}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '8px 12px',
            borderRadius: 4,
            border: `1px solid ${C.signOutBorder}`,
            background: C.signOutBg,
            color: C.signOutText,
            fontSize: 12,
            fontWeight: 500,
            fontFamily: "'IBM Plex Sans', sans-serif",
            cursor: 'pointer',
            letterSpacing: '0.02em',
            transition: 'background-color 150ms ease-out, color 150ms ease-out, border-color 150ms ease-out, transform 150ms cubic-bezier(0.23, 1, 0.32, 1)',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = C.signOutHoverBg;
            e.currentTarget.style.color = C.signOutHoverText;
            e.currentTarget.style.borderColor = '#A33F3F55';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = C.signOutBg;
            e.currentTarget.style.color = C.signOutText;
            e.currentTarget.style.borderColor = C.signOutBorder;
          }}
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
