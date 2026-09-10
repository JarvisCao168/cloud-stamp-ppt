const checkpoints = new Map<string, { timestamp: number; data: unknown }>();

export function saveCheckpoint(key: string, data: unknown): void {
  checkpoints.set(key, { timestamp: Date.now(), data });
}

export function loadCheckpoint<T>(key: string): T | null {
  const entry = checkpoints.get(key);
  if (!entry) return null;
  return entry.data as T;
}

export function clearCheckpoint(key: string): void {
  checkpoints.delete(key);
}

export function clearAllCheckpoints(): void {
  checkpoints.clear();
}
