import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import NumberingSelector from '@/components/NumberingSelector';
import * as apiModule from '@/api';

// Mock the API module
vi.mock('@/api', () => ({
  getNumberingStyles: vi.fn(),
}));

const mockGetNumberingStyles = apiModule.getNumberingStyles as unknown as ReturnType<typeof vi.fn>;

const mockStyles = [
  {
    id: 'numeric-dot',
    name: '数字序号·',
    type: 'numeric',
    symbols: ['1.', '2.', '3.'],
    description: '标准数字加点号',
    tags: ['商务', '正式'],
    max_depth: 3,
    preview_html: '<ol><li>第一项</li></ol>',
    is_system: true,
  },
  {
    id: 'chinese-clause',
    name: '中文顿号',
    type: 'chinese',
    symbols: ['一、', '二、', '三、'],
    description: '中文数字加顿号',
    tags: ['正式', '公文'],
    max_depth: 2,
    preview_html: '<p>一、第一项</p>',
    is_system: true,
  },
];

describe('NumberingSelector component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render loading state initially', () => {
    mockGetNumberingStyles.mockImplementation(() => new Promise(() => {}));
    
    render(<NumberingSelector />);
    expect(screen.getByText(/加载中/i)).toBeInTheDocument();
  });

  it('should render styles after loading', async () => {
    mockGetNumberingStyles.mockResolvedValue(mockStyles);
    
    render(<NumberingSelector />);
    
    await waitFor(() => {
      expect(screen.getByText('数字序号·')).toBeInTheDocument();
      expect(screen.getByText('中文顿号')).toBeInTheDocument();
    });
  });

  it('should display all style types in filter buttons', async () => {
    mockGetNumberingStyles.mockResolvedValue(mockStyles);
    
    render(<NumberingSelector />);
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: '全部' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '数字型' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '中文型' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '层级型' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '图形型' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '图标型' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '英文型' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '特殊型' })).toBeInTheDocument();
    });
  });

  it('should filter styles by type', async () => {
    mockGetNumberingStyles.mockResolvedValue(mockStyles);
    
    render(<NumberingSelector />);
    
    await waitFor(() => {
      expect(screen.getByText('数字序号·')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByRole('button', { name: '数字型' }));
    
    await waitFor(() => {
      expect(screen.getByText('数字序号·')).toBeInTheDocument();
      expect(screen.queryByText('中文顿号')).not.toBeInTheDocument();
    });
  });

  it('should call onChange when a style is selected', async () => {
    mockGetNumberingStyles.mockResolvedValue(mockStyles);
    
    const handleChange = vi.fn();
    render(<NumberingSelector onChange={handleChange} />);
    
    await waitFor(() => {
      expect(screen.getByText('数字序号·')).toBeInTheDocument();
    });
    
    const styleCards = document.querySelectorAll('.border-2');
    fireEvent.click(styleCards[0]);
    
    expect(handleChange).toHaveBeenCalledWith('numeric-dot');
  });

  it('should show preview when a style is selected', async () => {
    mockGetNumberingStyles.mockResolvedValue(mockStyles);
    
    render(<NumberingSelector value="numeric-dot" />);
    
    await waitFor(() => {
      expect(screen.getByText(/选中样式预览/i)).toBeInTheDocument();
    });
  });

  it('should not call onChange when disabled', async () => {
    mockGetNumberingStyles.mockResolvedValue(mockStyles);
    
    const handleChange = vi.fn();
    render(<NumberingSelector disabled onChange={handleChange} />);
    
    await waitFor(() => {
      expect(screen.getByText('数字序号·')).toBeInTheDocument();
    });
    
    const styleCards = document.querySelectorAll('.border-2');
    fireEvent.click(styleCards[0]);
    
    expect(handleChange).not.toHaveBeenCalled();
  });

  it('should fallback to local data when API fails', async () => {
    mockGetNumberingStyles.mockRejectedValue(new Error('API error'));
    
    render(<NumberingSelector />);
    
    await waitFor(() => {
      expect(screen.getByText('数字序号·')).toBeInTheDocument();
    });
  });

  it('should respect showPreview prop', async () => {
    mockGetNumberingStyles.mockResolvedValue(mockStyles);
    
    render(<NumberingSelector value="numeric-dot" showPreview={false} />);
    
    await waitFor(() => {
      expect(screen.queryByText(/选中样式预览/i)).not.toBeInTheDocument();
    });
  });
});
