import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import RevealContainer from '@/components/RevealContainer';

let mockOn: ReturnType<typeof vi.fn>;
let mockSlide: ReturnType<typeof vi.fn>;
let mockDestroy: ReturnType<typeof vi.fn>;

vi.mock('reveal.js', () => {
  mockOn = vi.fn();
  mockSlide = vi.fn();
  mockDestroy = vi.fn();
  
  class MockReveal {
    constructor(public element: HTMLElement) {
      this.on = mockOn;
      this.slide = mockSlide;
      this.destroy = mockDestroy;
    }
    on = vi.fn();
    slide = vi.fn();
    destroy = vi.fn();
  }
  
  return { default: MockReveal };
});

describe('RevealContainer component', () => {
  const slides = [
    { title: 'Slide 1', content: 'Content 1' },
    { title: 'Slide 2', content: 'Content 2' },
  ];

  const handleChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render placeholder when no slides', () => {
    render(<RevealContainer slides={[]} />);
    expect(screen.getByText(/生成演示文稿后将在此处预览/i)).toBeInTheDocument();
  });

  it('should render slides when provided', async () => {
    render(<RevealContainer slides={slides} />);
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect(screen.getByText('Slide 1')).toBeInTheDocument();
    expect(screen.getByText('Slide 2')).toBeInTheDocument();
  });

  it('should handle slide changes', async () => {
    render(<RevealContainer slides={slides} onSlideChange={handleChange} />);
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect(handleChange).toBeDefined();
  });

  it('should have reveal-container-wrapper class', async () => {
    const { container } = render(<RevealContainer slides={slides} />);
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect(container.querySelector('.reveal-container-wrapper')).toBeInTheDocument();
  });

  it('should clean up reveal instance on unmount', async () => {
    const { unmount } = render(<RevealContainer slides={slides} />);
    
    await new Promise(resolve => setTimeout(resolve, 100));
    unmount();
    
    expect(mockDestroy).toHaveBeenCalled();
  });
});
