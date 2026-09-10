import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CheckpointPanel from '@/components/CheckpointPanel';
import type { Checkpoint } from '@/types';

describe('CheckpointPanel', () => {
  const mockCheckpoints = new Map<string, Checkpoint>([
    ['cp-1', { id: 'cp-1', name: 'Outline Structure', description: 'Step 1', status: 'in_progress' }],
    ['cp-2', { id: 'cp-2', name: 'Template Selection', description: 'Step 2', status: 'pending' }],
    ['cp-3', { id: 'cp-3', name: 'Final Review', description: 'Step 3', status: 'completed' }],
  ]);

  const mockOnUpdate = vi.fn();
  const mockOnConfirm = vi.fn().mockResolvedValue(undefined);

  it('should not render in non-mastery mode', () => {
    const { container } = render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={mockOnUpdate}
        onConfirmCheckpoint={mockOnConfirm}
        mode="rapid"
      />
    );
    expect(container.innerHTML).toBe('');
  });

  it('should render in mastery mode', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={mockOnUpdate}
        onConfirmCheckpoint={mockOnConfirm}
        mode="mastery"
      />
    );
    expect(screen.getByText('检查点进度')).toBeDefined();
  });

  it('should display all checkpoints', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={mockOnUpdate}
        onConfirmCheckpoint={mockOnConfirm}
        mode="mastery"
      />
    );
    expect(screen.getByText('Outline Structure')).toBeDefined();
    expect(screen.getByText('Template Selection')).toBeDefined();
    expect(screen.getByText('Final Review')).toBeDefined();
  });

  it('should show Start button for pending checkpoints', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={mockOnUpdate}
        onConfirmCheckpoint={mockOnConfirm}
        mode="mastery"
      />
    );
    expect(screen.getByText('Start')).toBeDefined();
  });

  it('should show Complete button for in_progress checkpoints', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={mockOnUpdate}
        onConfirmCheckpoint={mockOnConfirm}
        mode="mastery"
      />
    );
    expect(screen.getByText('Complete')).toBeDefined();
  });

  it('should show Done for completed checkpoints', () => {
    const onlyCompleted = new Map<string, Checkpoint>([
      ['cp-1', { id: 'cp-1', name: 'Step 1', description: '', status: 'completed' }],
    ]);
    
    render(
      <CheckpointPanel
        checkpoints={onlyCompleted}
        onUpdateCheckpoint={mockOnUpdate}
        onConfirmCheckpoint={mockOnConfirm}
        mode="mastery"
      />
    );
    expect(screen.getByText('Done')).toBeDefined();
  });

  it('should call updateCheckpoint and onConfirmCheckpoint when Start is clicked', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={mockOnUpdate}
        onConfirmCheckpoint={mockOnConfirm}
        mode="mastery"
      />
    );
    
    fireEvent.click(screen.getByText('Start'));
    
    expect(mockOnUpdate).toHaveBeenCalledWith('cp-2', 'in_progress');
    expect(mockOnConfirm).toHaveBeenCalledWith('cp-2', 'confirm');
  });

  it('should call updateCheckpoint and onConfirmCheckpoint when Complete is clicked', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={mockOnUpdate}
        onConfirmCheckpoint={mockOnConfirm}
        mode="mastery"
      />
    );
    
    fireEvent.click(screen.getByText('Complete'));
    
    expect(mockOnUpdate).toHaveBeenCalledWith('cp-1', 'completed');
    expect(mockOnConfirm).toHaveBeenCalledWith('cp-1', 'confirm');
  });

  it('should calculate progress correctly', () => {
    render(
      <CheckpointPanel
        checkpoints={mockCheckpoints}
        onUpdateCheckpoint={mockOnUpdate}
        onConfirmCheckpoint={mockOnConfirm}
        mode="mastery"
      />
    );
    expect(screen.getByText('33%')).toBeDefined();
  });

  it('should show 100% when all checkpoints are completed', () => {
    const allDone = new Map<string, Checkpoint>([
      ['cp-1', { id: 'cp-1', name: 'Step 1', description: '', status: 'completed' }],
      ['cp-2', { id: 'cp-2', name: 'Step 2', description: '', status: 'completed' }],
    ]);

    render(
      <CheckpointPanel
        checkpoints={allDone}
        onUpdateCheckpoint={mockOnUpdate}
        onConfirmCheckpoint={mockOnConfirm}
        mode="mastery"
      />
    );
    
    expect(screen.getByText('100%')).toBeDefined();
  });

  it('should show 0% when no checkpoints are completed', () => {
    const noneDone = new Map<string, Checkpoint>([
      ['cp-1', { id: 'cp-1', name: 'Step 1', description: '', status: 'pending' }],
    ]);

    render(
      <CheckpointPanel
        checkpoints={noneDone}
        onUpdateCheckpoint={mockOnUpdate}
        onConfirmCheckpoint={mockOnConfirm}
        mode="mastery"
      />
    );
    
    expect(screen.getByText('0%')).toBeDefined();
  });
});
