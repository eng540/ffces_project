import { create } from "zustand";
import type { User, UserRole } from "@/types";
import { api } from "./api";

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  clearAuth: () => void;
  checkAuth: () => Promise<void>;
  hasRole: (role: UserRole) => boolean;
}

function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeRemoveItem(key: string) {
  try {
    localStorage.removeItem(key);
  } catch {
    // ignore storage errors (e.g., in private browsing)
  }
}

function safeSetItem(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // ignore storage errors
  }
}

function safeJSONParse<T>(value: string | null): T | null {
  if (!value) return null;
  try {
    return JSON.parse(value) as T;
  } catch {
    // corrupted data in localStorage
    return null;
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email: string, password: string) => {
    try {
      const response = (await api.login(email, password)) as {
        access_token: string;
        token_type: string;
        user: User;
      };

      safeSetItem("access_token", response.access_token);
      safeSetItem("user", JSON.stringify(response.user));

      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: () => {
    safeRemoveItem("access_token");
    safeRemoveItem("user");
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
    // Navigation is handled by the AuthGuard in layout.tsx
    // which watches isAuthenticated and redirects to /login
  },

  clearAuth: () => {
    safeRemoveItem("access_token");
    safeRemoveItem("user");
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },

  checkAuth: async () => {
    const token = safeGetItem("access_token");
    const storedUser = safeGetItem("user");

    if (token && storedUser) {
      const user = safeJSONParse<User>(storedUser);
      if (user) {
        set({ user, isAuthenticated: true, isLoading: false });
      } else {
        // Corrupted user data - clear everything
        safeRemoveItem("access_token");
        safeRemoveItem("user");
        set({ user: null, isAuthenticated: false, isLoading: false });
      }
    } else {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  hasRole: (role: UserRole) => {
    const state = get();
    return state.user?.role === role || state.user?.role === "admin";
  },
}));
