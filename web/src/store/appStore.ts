import { create } from 'zustand';

interface AppState {
  appTitle: string;
  isLoading: boolean;
  toggleLoading: () => void;
}

/**
 * Small Zustand store used to validate that state management is wired up.
 * Feature stores (e.g. passenger form state, prediction result) can be
 * added alongside this one as the app grows.
 */
export const useAppStore = create<AppState>((set) => ({
  appTitle: import.meta.env.VITE_APP_NAME ?? 'Titanic Survivors',
  isLoading: false,
  toggleLoading: () => set((state) => ({ isLoading: !state.isLoading })),
}));
