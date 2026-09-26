import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../contexts/AuthContext';
import { ThemeProvider } from '../contexts/ThemeContext';
import { FormConfigProvider } from '../contexts/FormConfigContext';

function renderWithProviders(ui: React.ReactElement, { route = '/' } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <FormConfigProvider>
            <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
          </FormConfigProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe('App providers', () => {
  it('renders without crashing', () => {
    renderWithProviders(<div data-testid="test">Hello</div>);
    expect(screen.getByTestId('test')).toBeInTheDocument();
  });
});
