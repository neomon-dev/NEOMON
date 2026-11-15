"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { User, Workspace, getCurrentUser, listWorkspaces, getUnreadNotificationCount, logoutUser } from "./collaboration";

interface AuthContextType {
  user: User | null;
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  unreadCount: number;
  isLoading: boolean;
  switchWorkspace: (workspaceId: string) => void;
  refreshAuth: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  workspaces: [],
  activeWorkspace: null,
  unreadCount: 0,
  isLoading: true,
  switchWorkspace: () => {},
  refreshAuth: async () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshAuth = useCallback(async () => {
    try {
      const u = await getCurrentUser();
      setUser(u);
      if (u) {
        const wsList = await listWorkspaces();
        setWorkspaces(wsList);

        // Determine active workspace
        const savedWsId = typeof window !== "undefined" ? localStorage.getItem("neomon_active_workspace_id") : null;
        let selected = wsList.find((w) => w.id === savedWsId);
        if (!selected && wsList.length > 0) {
          selected = wsList[0];
          if (typeof window !== "undefined") {
            localStorage.setItem("neomon_active_workspace_id", selected.id);
          }
        }
        setActiveWorkspace(selected || null);

        const count = await getUnreadNotificationCount();
        setUnreadCount(count);
      } else {
        setWorkspaces([]);
        setActiveWorkspace(null);
        setUnreadCount(0);
      }
    } catch {
      setUser(null);
      setWorkspaces([]);
      setActiveWorkspace(null);
      setUnreadCount(0);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshAuth();
  }, [refreshAuth]);

  const switchWorkspace = (workspaceId: string) => {
    const ws = workspaces.find((w) => w.id === workspaceId);
    if (ws) {
      setActiveWorkspace(ws);
      if (typeof window !== "undefined") {
        localStorage.setItem("neomon_active_workspace_id", ws.id);
      }
    }
  };

  const logout = async () => {
    await logoutUser();
    setUser(null);
    setWorkspaces([]);
    setActiveWorkspace(null);
    setUnreadCount(0);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        workspaces,
        activeWorkspace,
        unreadCount,
        isLoading,
        switchWorkspace,
        refreshAuth,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
