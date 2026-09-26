import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider, useTheme } from '../contexts/ThemeContext';

function ThemeTestComponent() {
  const { theme, isDark, toggleTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <span data-testid="isDark">{isDark.toString()}</span>
      <button onClick={toggleTheme}>Toggle</button>
    </div>
  );
}

describe('ThemeContext', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  it('defaults to light theme', () => {
    render(
      <ThemeProvider>
        <ThemeTestComponent />
      </ThemeProvider>
    );
    expect(screen.getByTestId('theme').textContent).toBe('light');
    expect(screen.getByTestId('isDark').textContent).toBe('false');
  });

  it('toggles to dark theme', () => {
    render(
      <ThemeProvider>
        <ThemeTestComponent />
      </ThemeProvider>
    );
    fireEvent.click(screen.getByText('Toggle'));
    expect(screen.getByTestId('theme').textContent).toBe('dark');
    expect(screen.getByTestId('isDark').textContent).toBe('true');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('persists theme to localStorage', () => {
    render(
      <ThemeProvider>
        <ThemeTestComponent />
      </ThemeProvider>
    );
    fireEvent.click(screen.getByText('Toggle'));
    expect(localStorage.getItem('governex-theme')).toBe('dark');
  });

  it('restores dark theme from localStorage', () => {
    localStorage.setItem('governex-theme', 'dark');
    render(
      <ThemeProvider>
        <ThemeTestComponent />
      </ThemeProvider>
    );
    expect(screen.getByTestId('theme').textContent).toBe('dark');
  });
});
