import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { auth as authApi, setToken, clearToken, type User, type StudentUser, type ApiError } from '../lib/api';

interface AuthState {
  user: (User | StudentUser) | null;
  loading: boolean;
  error: string | null;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  studentLogin: (username: string, password: string) => Promise<void>;
  signup: (data: { name: string; email: string; password: string }) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
  isEducator: boolean;
  isStudent: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, loading: true, error: null });

  const checkSession = useCallback(async () => {
    try {
      const res = await authApi.session();
      if (res.authenticated && res.user) {
        setState({ user: res.user, loading: false, error: null });
      } else {
        clearToken();
        setState({ user: null, loading: false, error: null });
      }
    } catch {
      clearToken();
      setState({ user: null, loading: false, error: null });
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('guide_token');
    if (token) {
      checkSession();
    } else {
      setState({ user: null, loading: false, error: null });
    }
  }, [checkSession]);

  const login = async (email: string, password: string) => {
    setState(s => ({ ...s, error: null, loading: true }));
    try {
      const res = await authApi.login(email, password);
      setToken(res.token);
      setState({ user: res.user, loading: false, error: null });
    } catch (e) {
      setState(s => ({ ...s, loading: false, error: (e as ApiError).message }));
      throw e;
    }
  };

  const studentLogin = async (username: string, password: string) => {
    setState(s => ({ ...s, error: null, loading: true }));
    try {
      const res = await authApi.studentLogin(username, password);
      setToken(res.token);
      setState({ user: res.user, loading: false, error: null });
    } catch (e) {
      setState(s => ({ ...s, loading: false, error: (e as ApiError).message }));
      throw e;
    }
  };

  const signup = async (data: { name: string; email: string; password: string }) => {
    setState(s => ({ ...s, error: null, loading: true }));
    try {
      const res = await authApi.signup(data);
      setToken(res.token);
      setState({ user: res.user, loading: false, error: null });
    } catch (e) {
      setState(s => ({ ...s, loading: false, error: (e as ApiError).message }));
      throw e;
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {}
    clearToken();
    setState({ user: null, loading: false, error: null });
  };

  const clearError = () => setState(s => ({ ...s, error: null }));

  const u = state.user as (User & Partial<StudentUser>) | null;
  const role: string = u && 'role' in u && u.role ? String(u.role) : '';
  const userType: string = u && 'user_type' in u && u.user_type ? String(u.user_type) : '';
  const isAdminFlag = u && 'is_admin' in u ? Boolean(u.is_admin) : false;

  const isEducator =
    userType === 'teacher' ||
    role === 'educator' ||
    role === 'admin' ||
    role === 'school_admin' ||
    role === 'school_educator';
  const isStudent = userType === 'student' || role === 'student';
  const isAdmin = isAdminFlag || role === 'admin' || role === 'school_admin';

  return (
    <AuthContext.Provider value={{
      ...state,
      login,
      studentLogin,
      signup,
      logout,
      clearError,
      isEducator,
      isStudent,
      isAdmin,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
