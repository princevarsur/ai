import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { jwtDecode } from 'jwt-decode';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

function isTokenValid(token) {
  if (!token) return false;
  try {
    const { exp } = jwtDecode(token);
    // Treat as expired 30 seconds early to avoid edge-case races
    return exp * 1000 > Date.now() + 30_000;
  } catch {
    return false;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser]           = useState(null);
  const [loading, setLoading]     = useState(true);

  // ── Bootstrap: restore session from localStorage ──────────────
  useEffect(() => {
    async function restoreSession() {
      const access  = localStorage.getItem('access_token');
      const refresh = localStorage.getItem('refresh_token');

      if (isTokenValid(access)) {
        try {
          const { data } = await authAPI.profile();
          setUser(data);
        } catch {
          clearTokens();
        }
      } else if (refresh) {
        // Access expired but refresh exists — try silent refresh
        try {
          const { data } = await authAPI.refresh(refresh);
          localStorage.setItem('access_token', data.access);
          const { data: profile } = await authAPI.profile();
          setUser(profile);
        } catch {
          clearTokens();
        }
      }
      setLoading(false);
    }
    restoreSession();
  }, []);

  function clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  }

  // ── login ──────────────────────────────────────────────────────
  const login = useCallback(async (username, password) => {
    const { data } = await authAPI.login(username, password);
    localStorage.setItem('access_token',  data.access);
    localStorage.setItem('refresh_token', data.refresh);

    const { data: profile } = await authAPI.profile();
    setUser(profile);
    return profile;
  }, []);

  // ── logout ─────────────────────────────────────────────────────
  const logout = useCallback(() => {
    clearTokens();
  }, []);

  // ── refreshToken ───────────────────────────────────────────────
  const refreshToken = useCallback(async () => {
    const refresh = localStorage.getItem('refresh_token');
    if (!refresh) throw new Error('No refresh token');
    const { data } = await authAPI.refresh(refresh);
    localStorage.setItem('access_token', data.access);
    return data.access;
  }, []);

  const value = {
    user,
    isAuthenticated: !!user,
    loading,
    login,
    logout,
    refreshToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
