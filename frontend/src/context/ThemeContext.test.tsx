import { act } from 'react';
import ReactDOM from 'react-dom/client';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import themeReducer from '../store/themeSlice';
import { ThemeProvider, useTheme } from './ThemeContext';

function TestButton() {
  const { isDark, toggleTheme } = useTheme();
  return (
    <button type="button" data-theme={isDark ? 'dark' : 'light'} onClick={toggleTheme}>
      toggle
    </button>
  );
}

describe('ThemeContext', () => {
  let container: HTMLDivElement;
  let root: ReactDOM.Root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    document.documentElement.className = 'dark';
    vi.mocked(localStorage.getItem).mockReturnValue('dark');
    vi.mocked(localStorage.setItem).mockClear();
  });

  afterEach(() => {
    root?.unmount();
    container.remove();
    document.documentElement.className = '';
  });

  it('toggles from dark to light without recursive failure', async () => {
    const store = configureStore({
      reducer: { theme: themeReducer },
    });

    await act(async () => {
      root = ReactDOM.createRoot(container);
      root.render(
        <Provider store={store}>
          <ThemeProvider>
            <TestButton />
          </ThemeProvider>
        </Provider>,
      );
    });

    const button = container.querySelector('button');
    expect(button?.dataset.theme).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);

    await act(async () => {
      button?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(button?.dataset.theme).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(localStorage.setItem).toHaveBeenLastCalledWith('theme', 'light');
  });
});
