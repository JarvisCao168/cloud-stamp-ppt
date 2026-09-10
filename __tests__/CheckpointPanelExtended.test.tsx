import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CheckpointPanel from '@/components/CheckpointPanel';

describe('CheckpointPanel component (extended)', () => {
  const mockCheckpoints = new Map([
    ['cp-1', { id: 'cp-1', name: 'Test CP 1', status: 'pending', description: 'Desc 1' }],
    ['cp-2', { id: 'cp-2', name: 'Test CP 2', status: 'in_progress', description: 'Desc 2' }],
    ['cp-3', { id: 'cp-3', name: 'Test CP 3', status: 'completed', description: 'Desc 3' }],
  ]);

  const onUpdateCheckpoint = vi.fn();
  const onConfirmCheckpoint = vi.fn();

  it('should render checkpoint list in mastery mode', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={onUpdateCheckpoint}
        onConfirmCheckpoint={onConfirmCheckpoint}
        mode="mastery"
      />
    );

    expect(screen.getByText('Test CP 1')).toBeInTheDocument();
    expect(screen.getByText('Test CP 2')).toBeInTheDocument();
    expect(screen.getByText('Test CP 3')).toBeInTheDocument();
  });

  it('should show Start button for pending checkpoints', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={onUpdateCheckpoint}
        onConfirmCheckpoint={onConfirmCheckpoint}
        mode="mastery"
      />
    );

    expect(screen.getByText('Start')).toBeInTheDocument();
  });

  it('should show Complete button for in_progress checkpoints', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={onUpdateCheckpoint}
        onConfirmCheckpoint={onConfirmCheckpoint}
        mode="mastery"
      />
    );

    expect(screen.getByText('Complete')).toBeInTheDocument();
  });

  it('should show Done text for completed checkpoints', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={onUpdateCheckpoint}
        onConfirmCheckpoint={onConfirmCheckpoint}
        mode="mastery"
      />
    );

    expect(screen.getByText('Done')).toBeInTheDocument();
  });

  it('should call handlers when Start button is clicked', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={onUpdateCheckpoint}
        onConfirmCheckpoint={onConfirmCheckpoint}
        mode="mastery"
      />
    );

    fireEvent.click(screen.getByText('Start'));

    expect(onUpdateCheckpoint).toHaveBeenCalledWith('cp-1', 'in_progress');
    expect(onConfirmCheckpoint).toHaveBeenCalledWith('cp-1', 'confirm');
  });

  it('should call handlers when Complete button is clicked', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={onUpdateCheckpoint}
        onConfirmCheckpoint={onConfirmCheckpoint}
        mode="mastery"
      />
    );

    fireEvent.click(screen.getByText('Complete'));

    expect(onUpdateCheckpoint).toHaveBeenCalledWith('cp-2', 'completed');
    expect(onConfirmCheckpoint).toHaveBeenCalledWith('cp-2', 'confirm');
  });

  it('should show progress percentage', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={onUpdateCheckpoint}
        onConfirmCheckpoint={onConfirmCheckpoint}
        mode="mastery"
      />
    );

    expect(screen.getByText(/33%/)).toBeInTheDocument();
  });

  it('should render progress bar', () => {
    const { container } = render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={onUpdateCheckpoint}
        onConfirmCheckpoint={onConfirmCheckpoint}
        mode="mastery"
      />
    );

    const progressBar = container.querySelector('.h-2.bg-gray-200');
    expect(progressBar).toBeInTheDocument();
  });

  it('should render null when mode is not mastery', () => {
    const { container } = render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={onUpdateCheckpoint}
        onConfirmCheckpoint={onConfirmCheckpoint}
        mode="rapid"
      />
    );

    expect(container.firstChild).toBeNull();
  });
});
