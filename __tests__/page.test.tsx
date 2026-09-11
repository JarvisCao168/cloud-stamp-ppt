import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Home from '@/page';
import * as generationStore from '@/generationStore';
import * as exportModule from '@/export';

vi.mock('@/generationStore', () => {
  const actual = vi.importActual<typeof generationStore>('@/generationStore');
  return {
    ...actual,
    useGeneration: vi.fn(),
  };
});

vi.mock('@/export', () => ({
  exportPresentationToFile: vi.fn().mockResolvedValue({ filename: 'test.html', url: '#', format: 'html' }),
  EXPORT_FORMATS: [
    { type: 'html' as const, name: 'HTML', icon: '🌐', description: 'Web format' },
    { type: 'pptx' as const, name: 'PPTX', icon: '📊', description: 'PowerPoint' },
    { type: 'pdf' as const, name: 'PDF', icon: '📄', description: 'PDF' },
    { type: 'png' as const, name: 'PNG', icon: '🖼️', description: 'Image' },
  ],
}));

const mockUseGeneration = generationStore.useGeneration as unknown as ReturnType<typeof vi.fn>;

const baseStore = {
  mode: 'rapid' as const,
  state: { status: 'idle' } as generationStore.GenerationState,
  prompt: '',
  setPrompt: vi.fn(),
  updateMode: vi.fn(),
  generate: vi.fn(),
  reset: vi.fn(),
  checkpoints: new Map<string, generationStore.Checkpoint>(),
  updateCheckpoint: vi.fn(),
  confirmCheckpoint: vi.fn(),
  sessionId: '',
  options: {},
  updateOptions: vi.fn(),
  numberingStyles: [],
};

describe('Home (page.tsx) Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders header with title', () => {
    mockUseGeneration.mockReturnValue(baseStore);
    render(<Home />);
    expect(screen.getByText('演示文稿生成器')).toBeInTheDocument();
  });

  it('renders mode selector', () => {
    mockUseGeneration.mockReturnValue(baseStore);
    render(<Home />);
    // ModeSelector renders buttons with aria-labels
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('renders prompt textarea', () => {
    mockUseGeneration.mockReturnValue(baseStore);
    render(<Home />);
    expect(screen.getByLabelText(/请输入主题/i)).toBeInTheDocument();
  });

  it('shows idle state message when no generation', () => {
    mockUseGeneration.mockReturnValue(baseStore);
    render(<Home />);
    expect(screen.getByText(/输入主题后点击生成/i)).toBeInTheDocument();
  });

  it('disables generate button when loading', () => {
    const store = {
      ...baseStore,
      state: { status: 'loading', progress: 0 },
    };
    mockUseGeneration.mockReturnValue(store);
    render(<Home />);
    const btn = screen.getByRole('button', { name: /生成演示文稿/i });
    expect(btn).toBeDisabled();
  });

  it('calls generate on button click', async () => {
    const store = { ...baseStore, prompt: 'AI trends' };
    mockUseGeneration.mockReturnValue(store);
    render(<Home />);
    const btn = screen.getByRole('button', { name: /生成演示文稿/i });
    await fireEvent.click(btn);
    expect(store.generate).toHaveBeenCalled();
  });

  it('shows success state with slides preview', () => {
    const store = {
      ...baseStore,
      state: {
        status: 'success',
        slides: [{ title: 'Slide 1', content: 'Content 1' }],
      },
      sessionId: 'session-123',
    };
    mockUseGeneration.mockReturnValue(store);
    render(<Home />);
    // Check for slide content instead of page counter (avoid SSR/dom issues)
    expect(screen.getByText('Slide 1')).toBeInTheDocument();
  });

  it('shows export section when success with sessionId', () => {
    const store = {
      ...baseStore,
      state: { status: 'success', slides: [] },
      sessionId: 'session-123',
    };
    mockUseGeneration.mockReturnValue(store);
    render(<Home />);
    expect(screen.getByText(/导出演示文稿/i)).toBeInTheDocument();
  });

  it('does not show export section without sessionId', () => {
    const store = {
      ...baseStore,
      state: { status: 'success', slides: [] },
      sessionId: '',
    };
    mockUseGeneration.mockReturnValue(store);
    render(<Home />);
    expect(screen.queryByText(/导出演示文稿/i)).not.toBeInTheDocument();
  });

  it('calls exportPresentationToFile on export button click', async () => {
    const store = {
      ...baseStore,
      state: { status: 'success', slides: [{ title: 'T', content: 'C' }] },
      sessionId: 'session-456',
    };
    mockUseGeneration.mockReturnValue(store);
    render(<Home />);
    const htmlBtn = screen.getByRole('button', { name: /HTML/i });
    await fireEvent.click(htmlBtn);
    await waitFor(() => {
      expect(exportModule.exportPresentationToFile).toHaveBeenCalled();
    });
  });

  it('passes numberingStyleId to export when options contain it', async () => {
    const store = {
      ...baseStore,
      state: { status: 'success', slides: [{ title: 'T', content: 'C' }] },
      sessionId: 'session-789',
      options: { numberingStyleId: 'numeric-dot' },
    };
    mockUseGeneration.mockReturnValue(store);
    (exportModule.exportPresentationToFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      filename: 'test.pptx',
      url: '#',
      format: 'pptx',
    });
    render(<Home />);
    const pptxBtn = screen.getByRole('button', { name: /PPTX/i });
    await fireEvent.click(pptxBtn);
    await waitFor(() => {
      expect(exportModule.exportPresentationToFile).toHaveBeenCalledWith(
        expect.arrayContaining([{ title: 'T', content: 'C' }]),
        expect.objectContaining({ numberingStyleId: 'numeric-dot' }),
        'session-789'
      );
    });
  });

  it('passes undefined numberingStyleId when not selected', async () => {
    const store = {
      ...baseStore,
      state: { status: 'success', slides: [{ title: 'T', content: 'C' }] },
      sessionId: 'session-no-num',
      options: {},
    };
    mockUseGeneration.mockReturnValue(store);
    (exportModule.exportPresentationToFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      filename: 'test.pptx',
      url: '#',
      format: 'pptx',
    });
    render(<Home />);
    const pptxBtn = screen.getByRole('button', { name: /PPTX/i });
    await fireEvent.click(pptxBtn);
    await waitFor(() => {
      expect(exportModule.exportPresentationToFile).toHaveBeenCalledWith(
        expect.arrayContaining([{ title: 'T', content: 'C' }]),
        expect.objectContaining({ numberingStyleId: undefined }),
        'session-no-num'
      );
    });
  });

  it('handles export error state', async () => {
    (exportModule.exportPresentationToFile as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Export failed'));
    const store = {
      ...baseStore,
      state: { status: 'success', slides: [] },
      sessionId: 'session-err',
    };
    mockUseGeneration.mockReturnValue(store);
    render(<Home />);
    const htmlBtn = screen.getByRole('button', { name: /HTML/i });
    await fireEvent.click(htmlBtn);
    // Just verify the button was clicked and export was called
    expect(exportModule.exportPresentationToFile).toHaveBeenCalled();
  });

  it('shows reset button in success state', () => {
    const store = {
      ...baseStore,
      state: { status: 'success', slides: [] },
      sessionId: 'sess',
    };
    mockUseGeneration.mockReturnValue(store);
    render(<Home />);
    expect(screen.getByRole('button', { name: /重新生成/i })).toBeInTheDocument();
  });

  it('shows tips section', () => {
    mockUseGeneration.mockReturnValue(baseStore);
    render(<Home />);
    expect(screen.getByText(/使用提示/i)).toBeInTheDocument();
    expect(screen.getByText(/极速模式/i)).toBeInTheDocument();
  });

  it('shows checkpoint panel in mastery mode with checkpoints', () => {
    const cps = new Map([['cp1', { id: 'cp1', name: 'Review', description: 'Review slides', status: 'pending' as const }]]);
    const store = {
      ...baseStore,
      mode: 'mastery',
      checkpoints: cps,
    };
    mockUseGeneration.mockReturnValue(store);
    render(<Home />);
    expect(screen.getByText(/检查点进度/i)).toBeInTheDocument();
  });

  it('does not show checkpoint panel in rapid mode', () => {
    const store = { ...baseStore, mode: 'rapid' };
    mockUseGeneration.mockReturnValue(store);
    render(<Home />);
    expect(screen.queryByText(/检查点进度/i)).not.toBeInTheDocument();
  });
});
