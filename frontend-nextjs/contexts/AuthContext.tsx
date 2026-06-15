'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

const APP_AUTH_TOKEN_KEY = 'app_auth_token';
const APP_AUTH_USER_KEY = 'app_auth_user';

const DEV_MODE = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
const DEV_SKIP_AUTH = process.env.NEXT_PUBLIC_DEV_SKIP_AUTH === 'true';

export interface User {
  user_id: number;
  username: string;
  name?: string;
  email?: string;
  display_name?: string;
  avatar_url?: string;
  roles?: string[];
  tier?: 'free' | 'basic' | 'professional' | 'enterprise';
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  logout: () => void;
  refreshUser: () => void;
}

const DEV_USER: User = {
  user_id: 9999,
  username: 'dev_user',
  name: '开发测试用户',
  display_name: '开发测试用户',
  email: 'dev@localhost',
  roles: ['administrator'],
  tier: 'enterprise',
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function readStoredUser(): User | null {
  if (typeof window === 'undefined') return null;
  const token = localStorage.getItem(APP_AUTH_TOKEN_KEY);
  const userJson = localStorage.getItem(APP_AUTH_USER_KEY);
  if (!token || !userJson) return null;

  try {
    return JSON.parse(userJson) as User;
  } catch {
    localStorage.removeItem(APP_AUTH_TOKEN_KEY);
    localStorage.removeItem(APP_AUTH_USER_KEY);
    return null;
  }
}

function storeSession(token: string, user: User) {
  localStorage.setItem(APP_AUTH_TOKEN_KEY, token);
  localStorage.setItem(APP_AUTH_USER_KEY, JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem(APP_AUTH_TOKEN_KEY);
  localStorage.removeItem(APP_AUTH_USER_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const refreshUser = () => {
    setUser(readStoredUser());
  };

  useEffect(() => {
    if (DEV_MODE && DEV_SKIP_AUTH) {
      storeSession('dev-token-mock', DEV_USER);
      setUser(DEV_USER);
      setIsLoading(false);
      return;
    }

    refreshUser();
    setIsLoading(false);

    const handleAuthUpdated = () => refreshUser();
    window.addEventListener('app-auth-updated', handleAuthUpdated);
    return () => window.removeEventListener('app-auth-updated', handleAuthUpdated);
  }, []);

  const logout = () => {
    clearSession();
    setUser(null);
    router.push('/auth/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: Boolean(user),
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
