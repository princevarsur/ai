import { createContext, useContext, useState, useEffect } from 'react';
import { jwtDecode } from 'jwt-decode';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const isTokenValid = (token) => {
    if (!token) return false;
    try {
      const decoded = jwtDecode(token);
      return decoded.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  };

  const loadUser = () => {
    const token = localStorage.getItem('access_token');
    if (token && isTokenValid(token)) {
      const decoded = jwtDecode(token);
      setUser({
        id: decoded.user_id,
        username: decoded.username,
      });
    } else {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadUser();
  }, []);

  const login = async (username, password) => {
    try {
      const { data } = await authAPI.login(username, password);
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      
      const decoded = jwtDecode(data.access);
      setUser({
        id: decoded.user_id,
        username: decoded.username,
      });
      
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed',
      };
    }
  };

  const register = async (userData) => {
    try {
      await authAPI.register(userData);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Registration failed',
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  const refreshToken = async () => {
    const refresh = localStorage.getItem('refresh_token');
    if (!refresh) return false;

    try {
      const { data } = await authAPI.refresh(refresh);
      localStorage.setItem('access_token', data.access);
      return true;
    } catch {
      logout();
      return false;
    }
  };

  const value = {
    user,
    isAuthenticated: !!user,
    loading,
    login,
    register,
    logout,
    refreshToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
