import { createSlice } from '@reduxjs/toolkit';

export type { Theme } from '../types';

interface ThemeState {
  theme: 'light' | 'dark';
}

const getInitialTheme = (): 'light' | 'dark' => {
  if (typeof window === 'undefined') return 'dark';
  const stored = localStorage.getItem('theme');
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

const initialState: ThemeState = {
  theme: getInitialTheme(),
};

const themeSlice = createSlice({
  name: 'theme',
  initialState,
  reducers: {
    toggleTheme(state) {
      state.theme = state.theme === 'dark' ? 'light' : 'dark';
    },
  },
});

// Type-safe action creator workaround: return the action object explicitly
export const toggleTheme = (): { type: 'theme/toggleTheme' } => ({ type: 'theme/toggleTheme' });

export const selectTheme = (state: { theme: ThemeState }) => state.theme.theme;
export const selectIsDark = (state: { theme: ThemeState }) => state.theme.theme === 'dark';

export default themeSlice.reducer;