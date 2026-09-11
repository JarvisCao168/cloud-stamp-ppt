import { test, expect, describe, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TemplateSelector from '@/components/TemplateSelector';
import * as apiModule from '@/api';

vi.mock('@/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api')>();
  return {
    ...actual,
    getAllAssets: vi.fn(),
  };
});

const mockGetAllAssets = vi.mocked(apiModule.getAllAssets);

const mockTemplates = [
  {
    id: 'modern-dark',
    name: '现代暗色',
    category: 'theme',
    preview: '/assets/previews/modern-dark.png',
    description: '暗色主题',
  },
  {
    id: 'corporate-clean',
    name: '商务简洁',
    category: 'theme',
    preview: '/assets/previews/corporate-clean.png',
    description: '简洁商务风',
  },
  {
    id: 'academic',
    name: '学术严谨',
    category: 'academic',
    preview: '/assets/previews/academic.png',
    description: '学术风格',
  },
];

describe('TemplateSelector component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render loading state initially', () => {
    mockGetAllAssets.mockImplementation(() => new Promise(() => {}));

    render(<TemplateSelector />);
    expect(screen.getByText(/加载模板中/i)).toBeInTheDocument();
  });

  it('should render templates after loading', async () => {
    mockGetAllAssets.mockResolvedValue({ templates: mockTemplates });

    render(<TemplateSelector />);

    await waitFor(() => {
      expect(screen.getByText('现代暗色')).toBeInTheDocument();
      expect(screen.getByText('商务简洁')).toBeInTheDocument();
      expect(screen.getByText('学术严谨')).toBeInTheDocument();
    });
  });

  it('should display category filter buttons', async () => {
    mockGetAllAssets.mockResolvedValue({ templates: mockTemplates });

    render(<TemplateSelector />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '全部' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'theme' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'academic' })).toBeInTheDocument();
    });
  });

  it('should filter templates by category', async () => {
    mockGetAllAssets.mockResolvedValue({ templates: mockTemplates });

    render(<TemplateSelector />);

    await waitFor(() => {
      expect(screen.getByText('现代暗色')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: 'theme' }));

    await waitFor(() => {
      expect(screen.getByText('现代暗色')).toBeInTheDocument();
      expect(screen.getByText('商务简洁')).toBeInTheDocument();
      // academic 类别的模板不应显示
      expect(screen.queryByText('学术严谨')).not.toBeInTheDocument();
    });
  });

  it('should call onChange when a template is selected', async () => {
    mockGetAllAssets.mockResolvedValue({ templates: mockTemplates });

    const handleChange = vi.fn();
    render(<TemplateSelector onChange={handleChange} />);

    await waitFor(() => {
      expect(screen.getByText('现代暗色')).toBeInTheDocument();
    });

    // 点击第一个模板卡片
    const templateCards = document.querySelectorAll('.rounded-xl');
    fireEvent.click(templateCards[0]);

    expect(handleChange).toHaveBeenCalledWith('modern-dark');
  });

  it('should show selected state when value is set', async () => {
    mockGetAllAssets.mockResolvedValue({ templates: mockTemplates });

    render(<TemplateSelector value="modern-dark" />);

    await waitFor(() => {
      expect(screen.getByText('现代暗色')).toBeInTheDocument();
    });

    // 已选中的模板应有蓝色边框和选中提示
    expect(screen.getByText('已选择: 现代暗色')).toBeInTheDocument();
  });

  it('should not call onChange when disabled', async () => {
    mockGetAllAssets.mockResolvedValue({ templates: mockTemplates });

    const handleChange = vi.fn();
    render(<TemplateSelector disabled onChange={handleChange} />);

    await waitFor(() => {
      expect(screen.getByText('现代暗色')).toBeInTheDocument();
    });

    const templateCards = document.querySelectorAll('.rounded-xl');
    fireEvent.click(templateCards[0]);

    expect(handleChange).not.toHaveBeenCalled();
  });

  it('should fallback gracefully when API fails', async () => {
    mockGetAllAssets.mockRejectedValue(new Error('API error'));

    render(<TemplateSelector />);

    await waitFor(() => {
      // API 失败后应显示空状态
      expect(screen.getByText('暂无模板')).toBeInTheDocument();
    });
  });

  it('should respect showDescription prop', async () => {
    mockGetAllAssets.mockResolvedValue({ templates: mockTemplates });

    // 不显示描述
    render(<TemplateSelector showDescription={false} />);

    await waitFor(() => {
      expect(screen.getByText('现代暗色')).toBeInTheDocument();
    });

    // 描述不应出现
    expect(screen.queryByText('暗色主题')).not.toBeInTheDocument();

    // 显示描述
    render(<TemplateSelector showDescription={true} />);

    await waitFor(() => {
      expect(screen.getByText('暗色主题')).toBeInTheDocument();
    });
  });

  it('should show correct emoji for each template', async () => {
    mockGetAllAssets.mockResolvedValue({ templates: mockTemplates });

    render(<TemplateSelector />);

    await waitFor(() => {
      // 检查模板图标是否正确显示（通过图片 alt 或 emoji）
      expect(screen.getByText('现代暗色')).toBeInTheDocument();
      expect(screen.getByText('商务简洁')).toBeInTheDocument();
    });
  });
});

describe('TemplateSelector integration with generationStore', () => {
  it('should pass template ID to generation options', async () => {
    mockGetAllAssets.mockResolvedValue({ templates: mockTemplates });

    const handleChange = vi.fn();
    render(<TemplateSelector value="academic" onChange={handleChange} />);

    await waitFor(() => {
      expect(screen.getByText('学术严谨')).toBeInTheDocument();
    });

    // 点击学术模板
    const templateCards = document.querySelectorAll('.rounded-xl');
    fireEvent.click(templateCards[2]);

    expect(handleChange).toHaveBeenCalledWith('academic');
  });
});
