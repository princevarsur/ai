import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import { NAV_ITEMS } from '../utils/constants';

export default function Layout({ children }) {
  const { pathname } = useLocation();
  const current = NAV_ITEMS.find(n =>
    pathname === n.path || pathname.startsWith(n.path + '/')
  );
  const pageTitle = current?.label ?? 'Themis';

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />

      <div style={{
        marginLeft: 'var(--sidebar-w)',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
      }}>
        {/* Header */}
        <header style={{
          height: 'var(--header-h)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 32px',
          borderBottom: '1px solid var(--hairline)',
          background: 'var(--bg)',
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}>
          <h3 style={{ fontWeight: 500, color: 'var(--ink)' }}>{pageTitle}</h3>
        </header>

        {/* Content */}
        <main style={{
          flex: 1,
          padding: '36px 48px',
          background: 'var(--bg)',
          overflowY: 'auto',
          maxWidth: 1540,
          margin: '0 auto',
          width: '100%',
        }}>
          {children}
        </main>
      </div>
    </div>
  );
}
