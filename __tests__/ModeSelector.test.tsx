import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ModeSelector from '@/components/ModeSelector';

describe('ModeSelector component', () => {
  const handleChange = vi.fn();

  it('should render all three modes', () => {
    render(<ModeSelector currentMode="rapid" onModeChange={handleChange} />);
    
    expect(screen.getByText('极速')).toBeInTheDocument();
    expect(screen.getByText('协作')).toBeInTheDocument();
    expect(screen.getByText('掌控')).toBeInTheDocument();
  });

  it('should highlight active mode', () => {
    render(<ModeSelector currentMode="mastery" onModeChange={handleChange} />);
    
    const masteryButton = screen.getByRole('button', { name: /选择掌控模式/i });
    expect(masteryButton).toHaveClass('scale-105');
  });

  it('should call onModeChange when button is clicked', () => {
    render(<ModeSelector currentMode="rapid" onModeChange={handleChange} />);
    
    const collaborativeButton = screen.getByRole('button', { name: /选择协作模式/i });
    collaborativeButton.click();
    
    expect(handleChange).toHaveBeenCalledWith('collaborative');
  });

  it('should display mode descriptions', () => {
    render(<ModeSelector currentMode="rapid" onModeChange={handleChange} />);
    
    expect(screen.getByText('快速生成，精简内容')).toBeInTheDocument();
    expect(screen.getByText('多人协作，互动增强')).toBeInTheDocument();
    expect(screen.getByText('深度定制，完整控制')).toBeInTheDocument();
  });

  it('should have color indicators for each mode', () => {
    const { container } = render(<ModeSelector currentMode="rapid" onModeChange={handleChange} />);
    
    const indicators = container.querySelectorAll('[aria-hidden="true"]');
    expect(indicators.length).toBeGreaterThanOrEqual(3);
  });
});
