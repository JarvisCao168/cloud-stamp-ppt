import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import LoadingState from '@/components/LoadingState';

describe('LoadingState component', () => {
  it('should render default message', () => {
    render(<LoadingState />);
    expect(screen.getByText(/正在生成演示文稿/i)).toBeInTheDocument();
  });

  it('should render custom message', () => {
    render(<LoadingState message="Custom loading message" />);
    expect(screen.getByText('Custom loading message')).toBeInTheDocument();
  });

  it('should have spinner animation class', () => {
    const { container } = render(<LoadingState />);
    const spinner = container.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('should render helper text', () => {
    render(<LoadingState />);
    expect(screen.getByText(/请稍候/i)).toBeInTheDocument();
  });
});
