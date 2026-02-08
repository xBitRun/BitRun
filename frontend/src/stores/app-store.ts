/**
 * Application Store
 * 
 * Global app state management with Zustand.
 */

import { create } from 'zustand';

interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message?: string;
  timestamp: Date;
}

interface AppState {
  // UI State
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark';
  
  // Notifications
  notifications: Notification[];
  
  // WebSocket
  wsConnected: boolean;
  
  // Actions
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  setWsConnected: (connected: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  sidebarCollapsed: false,
  theme: 'dark',
  notifications: [],
  wsConnected: false,

  // Toggle sidebar
  toggleSidebar: () => set((state) => ({ 
    sidebarCollapsed: !state.sidebarCollapsed 
  })),

  // Set sidebar state
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

  // Set theme
  setTheme: (theme) => set({ theme }),

  // Add notification
  addNotification: (notification) => set((state) => ({
    notifications: [
      ...state.notifications,
      {
        ...notification,
        id: crypto.randomUUID(),
        timestamp: new Date(),
      },
    ],
  })),

  // Remove notification
  removeNotification: (id) => set((state) => ({
    notifications: state.notifications.filter((n) => n.id !== id),
  })),

  // Clear all notifications
  clearNotifications: () => set({ notifications: [] }),

  // Set WebSocket connection status
  setWsConnected: (connected) => set({ wsConnected: connected }),
}));
