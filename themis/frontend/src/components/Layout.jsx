import Sidebar from './Sidebar';

const Layout = ({ children, title }) => {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      
      <div style={{
        marginLeft: 'var(--sidebar-width)',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
      }}>
        {/* Header */}
        <header style={{
          height: 'var(--header-height)',
          background: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 2rem',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}>
          <h1 style={{
            fontSize: '1.5rem',
            fontWeight: 600,
            margin: 0,
          }}>
            {title}
          </h1>
        </header>

        {/* Main content */}
        <main style={{
          flex: 1,
          padding: '2rem',
          background: 'var(--bg-primary)',
        }}>
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
