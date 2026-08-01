import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  DashboardOutlined,
  UploadOutlined,
  FileTextOutlined,
  SearchOutlined,
  BookOutlined,
  LineChartOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';

const Sidebar = () => {
  const { user, logout } = useAuth();

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: <DashboardOutlined /> },
    { path: '/upload', label: 'Upload Policy', icon: <UploadOutlined /> },
    { path: '/reports', label: 'Scan History', icon: <FileTextOutlined /> },
    { path: '/what-if', label: 'What-If Checker', icon: <SearchOutlined /> },
  ];

  return (
    <aside style={{
      width: 'var(--sidebar-width)',
      height: '100vh',
      background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-color)',
      display: 'flex',
      flexDirection: 'column',
      position: 'fixed',
      left: 0,
      top: 0,
      zIndex: 100,
    }}>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          padding: '1.5rem',
          borderBottom: '1px solid var(--border-color)',
        }}
      >
        <h2 style={{
          fontSize: '1.25rem',
          fontWeight: 700,
          color: 'var(--accent-primary)',
          margin: 0,
          letterSpacing: '0.5px',
        }}>
          THEMIS
        </h2>
        <p style={{
          fontSize: '0.75rem',
          color: 'var(--text-tertiary)',
          margin: 0,
          marginTop: '0.25rem',
        }}>
          Legal Compliance AI
        </p>
      </motion.div>

      {/* Navigation */}
      <nav style={{
        flex: 1,
        padding: '1rem 0',
        overflowY: 'auto',
      }}>
        {navItems.map((item, index) => (
          <NavLink
            key={item.path}
            to={item.path}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '0.875rem 1.5rem',
              color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
              background: isActive ? 'rgba(34, 211, 238, 0.1)' : 'transparent',
              borderLeft: isActive ? '3px solid var(--accent-primary)' : '3px solid transparent',
              textDecoration: 'none',
              transition: 'all var(--transition-fast)',
              fontSize: '0.9375rem',
              fontWeight: isActive ? 600 : 500,
            })}
          >
            <motion.span
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              style={{ fontSize: '1.125rem', display: 'flex' }}
            >
              {item.icon}
            </motion.span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User info + logout */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        style={{
          padding: '1rem',
          borderTop: '1px solid var(--border-color)',
          background: 'var(--bg-primary)',
        }}
      >

        <button
          onClick={logout}
          style={{
            width: '100%',
            padding: '0.75rem',
            background: 'transparent',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            color: 'var(--text-secondary)',
            fontWeight: 500,
            fontSize: '0.9375rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            transition: 'all var(--transition-fast)',
          }}
          onMouseEnter={(e) => {
            e.target.style.borderColor = 'var(--error)';
            e.target.style.color = 'var(--error)';
          }}
          onMouseLeave={(e) => {
            e.target.style.borderColor = 'var(--border-color)';
            e.target.style.color = 'var(--text-secondary)';
          }}
        >
          <LogoutOutlined />
          Logout
        </button>
      </motion.div>
    </aside>
  );
};

export default Sidebar;
