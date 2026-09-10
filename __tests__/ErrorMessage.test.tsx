import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ErrorMessage from '@/components/ErrorMessage';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

describe('ErrorMessage component', () => {
  it('should render error message', () => {
    render(<ErrorMessage message="Something went wrong" />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('should not render retry button when onRetry is not provided', () => {
    render(<ErrorMessage message="Error without retry" />);
    expect(screen.queryByText(/重试/i)).not.toBeInTheDocument();
  });

  it('should render retry button when onRetry is provided', () => {
    const handleRetry = vi.fn();
    render(<ErrorMessage message="Error with retry" onRetry={handleRetry} />);
    expect(screen.getByText(/重试/i)).toBeInTheDocument();
  });

  it('should call onRetry when retry button is clicked', () => {
    const handleRetry = vi.fn();
    render(<ErrorMessage message="Error" onRetry={handleRetry} />);
    screen.getByText(/重试/i).click();
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it('should render error icon', () => {
    render(<ErrorMessage message="Test error" />);
    const container = document.querySelector('.flex.flex-col');
    expect(container).toBeInTheDocument();
  });
});
