'use client';

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';

const API_BASE = typeof window !== 'undefined'
  ? `http://${window.location.hostname}:8001/api/v1`
  : 'http://localhost:8001/api/v1';

interface AuthUser {
  id: string;
  email: string | null;
  display_name: string;
  avatar_url: string | null;
  home_lat: number | null;
  home_lon: number | null;
  strava_athlete_id: number | null;
  onboarding_done: boolean;
  strava_connected?: boolean;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithStrava: (code: string) => Promise<void>;
  connectStrava: (code: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => void;
  updateProfile: (data: { display_name?: string; home_lat?: number; home_lon?: number }) => Promise<void>;
  completeOnboarding: (data: { home_lat: number; home_lon: number; bike_name?: string; bike_type?: string }) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

async function authFetch(path: string, opts?: RequestInit & { token?: string }) {
  const { token, ...fetchOpts } = opts || {};
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      method: fetchOpts.method,
      body: fetchOpts.body,
      headers,
    });
  } catch {
    throw new Error('Server nicht erreichbar');
  }
  let json;
  try {
    json = await resp.json();
  } catch {
    throw new Error(`Server-Fehler (${resp.status})`);
  }
  if (json.status === 'error') {
    throw new Error(json.error?.message ?? 'Unbekannter Fehler');
  }
  return json.data;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore session on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('trailpilot_token');
    if (savedToken) {
      setToken(savedToken);
      authFetch('/auth/me', { token: savedToken })
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('trailpilot_token');
          localStorage.removeItem('trailpilot_refresh_token');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const saveTokens = useCallback((accessToken: string, refreshToken: string) => {
    localStorage.setItem('trailpilot_token', accessToken);
    localStorage.setItem('trailpilot_refresh_token', refreshToken);
    setToken(accessToken);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await authFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (!data?.access_token) throw new Error('Login fehlgeschlagen');
    saveTokens(data.access_token, data.refresh_token);
    setUser(data.user);
  }, [saveTokens]);

  const loginWithStrava = useCallback(async (code: string) => {
    const data = await authFetch('/auth/strava/callback', {
      method: 'POST',
      body: JSON.stringify({ code }),
    });
    if (!data?.access_token) throw new Error('Strava Login fehlgeschlagen');
    saveTokens(data.access_token, data.refresh_token);
    setUser(data.user);
  }, [saveTokens]);

  const connectStrava = useCallback(async (code: string) => {
    if (!token) throw new Error('Not authenticated');
    const data = await authFetch('/auth/strava/connect', {
      method: 'POST',
      body: JSON.stringify({ code }),
      token,
    });
    setUser(data.user);
  }, [token]);

  const register = useCallback(async (email: string, password: string, displayName: string) => {
    const data = await authFetch('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName }),
    });
    if (!data?.access_token) throw new Error('Registrierung fehlgeschlagen');
    saveTokens(data.access_token, data.refresh_token);
    setUser(data.user);
  }, [saveTokens]);

  const logout = useCallback(() => {
    if (token) {
      authFetch('/auth/logout', { method: 'POST', token }).catch(() => {});
    }
    localStorage.removeItem('trailpilot_token');
    localStorage.removeItem('trailpilot_refresh_token');
    setToken(null);
    setUser(null);
  }, [token]);

  const updateProfile = useCallback(async (data: { display_name?: string; home_lat?: number; home_lon?: number }) => {
    if (!token) return;
    const updated = await authFetch('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
      token,
    });
    setUser(updated);
  }, [token]);

  const completeOnboarding = useCallback(async (data: { home_lat: number; home_lon: number; bike_name?: string; bike_type?: string }) => {
    if (!token) return;
    const result = await authFetch('/auth/me/onboarding', {
      method: 'POST',
      body: JSON.stringify(data),
      token,
    });
    setUser(result.user);
  }, [token]);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, loginWithStrava, connectStrava, register, logout, updateProfile, completeOnboarding }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
