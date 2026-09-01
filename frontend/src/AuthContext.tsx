import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { AuthUser } from './types';

const TOKEN_KEY = 'metalex_token';

// Demo user used when there is no backend (Vercel standalone deployment)
const DEMO_USER: AuthUser = {
  id: 'demo',
  username: 'demo_officer',
  email: 'demo@metalex.gov.in',
  full_name: 'Inspector Sharma',
  role: 'officer',
};

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, user: AuthUser) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: DEMO_USER,
  token: null,
  isLoading: false,
  login: () => {},
  logout: () => {},
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Start with demo user so the UI renders immediately with no blank flash
  const [user, setUser] = useState<AuthUser | null>(DEMO_USER);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading] = useState(false); // never block render

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) return; // no stored token → keep demo user, nothing to do

    // Try to verify stored token against backend, but with a strict 4s timeout.
    // If the backend is unreachable (Vercel standalone), we simply keep the demo user.
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);

    const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${stored}` },
      signal: controller.signal,
    })
      .then((res) => {
        if (!res.ok) throw new Error('invalid token');
        return res.json();
      })
      .then((u) => {
        setToken(stored);
        setUser(u as AuthUser);
      })
      .catch(() => {
        // Backend unreachable or token invalid — clear token, stay as demo user
        localStorage.removeItem(TOKEN_KEY);
        setUser(DEMO_USER);
      })
      .finally(() => clearTimeout(timeout));
  }, []);

  const login = useCallback((newToken: string, newUser: AuthUser) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
    setUser(newUser);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(DEMO_USER); // revert to demo user instead of null
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
