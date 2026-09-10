import { describe, it, expect } from 'vitest';
import { saveCheckpoint, loadCheckpoint, clearCheckpoint, clearAllCheckpoints } from '@/checkpoints';

describe('checkpoints', () => {
  beforeEach(() => {
    clearAllCheckpoints();
  });

  it('should save and load a checkpoint', () => {
    saveCheckpoint('test-id', { title: 'Test' });
    const result = loadCheckpoint('test-id');
    expect(result).toEqual({ title: 'Test' });
  });

  it('should return null for missing checkpoint', () => {
    const result = loadCheckpoint('missing');
    expect(result).toBeNull();
  });

  it('should clear a single checkpoint', () => {
    saveCheckpoint('test-id', { data: 'value' });
    clearCheckpoint('test-id');
    const result = loadCheckpoint('test-id');
    expect(result).toBeNull();
  });

  it('should clear all checkpoints', () => {
    saveCheckpoint('id1', { data: '1' });
    saveCheckpoint('id2', { data: '2' });
    clearAllCheckpoints();
    expect(loadCheckpoint('id1')).toBeNull();
    expect(loadCheckpoint('id2')).toBeNull();
  });

  it('should handle different data types', () => {
    saveCheckpoint('num', 42);
    expect(loadCheckpoint('num')).toBe(42);
    saveCheckpoint('str', 'hello');
    expect(loadCheckpoint('str')).toBe('hello');
    saveCheckpoint('arr', [1, 2, 3]);
    expect(loadCheckpoint('arr')).toEqual([1, 2, 3]);
  });
});
