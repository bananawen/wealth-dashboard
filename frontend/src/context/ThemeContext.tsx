import { createContext, useCallback, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { toggleTheme, selectTheme, selectIsDark } from '../store/themeSlice';
import type { ThemeContextValue } from '../types';
import type { AppDispatch } from '../store';

export const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const dispatch = useDispatch<AppDispatch>();
  const theme = useSelector(selectTheme);
  const isDark = useSelector(selectIsDark);

  const handleToggleTheme = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    dispatch(toggleTheme() as any);
  }, [dispatch]);

  useEffect(() => {
    localStorage.setItem('theme', theme);
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  const value: ThemeContextValue = { theme, toggleTheme: handleToggleTheme, isDark };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const dispatch = useDispatch<AppDispatch>();
  const theme = useSelector(selectTheme);
  const isDark = useSelector(selectIsDark);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const toggleTheme = useCallback(() => { dispatch(toggleTheme() as unknown as any); }, [dispatch]);
  return { theme, toggleTheme, isDark };
}