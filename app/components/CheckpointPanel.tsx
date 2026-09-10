'use client';

import { Checkpoint } from '@/types';

interface CheckpointPanelProps {
  checkpoints: Map<string, Checkpoint>;
  onUpdateCheckpoint: (id: string, status: Checkpoint['status'], data?: unknown) => void;
  onConfirmCheckpoint: (id: string, action: 'confirm' | 'edit' | 'regenerate' | 'select') => void | Promise<void>;
  mode: string;
}

export default function CheckpointPanel({ checkpoints, onUpdateCheckpoint, onConfirmCheckpoint, mode }: CheckpointPanelProps) {
  if (mode !== 'mastery') return null;

  const checkpointList = Array.from(checkpoints.values());

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        检查点进度
      </h2>
      
      <div className="space-y-3">
        {checkpointList.map((cp) => (
          <div
            key={cp.id}
            className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50"
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                cp.status === 'completed' 
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-600' 
                  : cp.status === 'in_progress'
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600'
                  : 'bg-gray-100 dark:bg-gray-600 text-gray-400'
              }`}>
                {cp.status === 'completed' ? (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : cp.status === 'in_progress' ? (
                  <div className="w-3 h-3 rounded-full bg-blue-500 animate-pulse" />
                ) : (
                  <span className="text-sm font-medium">{checkpointList.indexOf(cp) + 1}</span>
                )}
              </div>
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {cp.name.replace(/_/g, ' ')}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {cp.description}
                </p>
              </div>
            </div>
            
            <div className="flex gap-2">
              {cp.status === 'pending' && (
                <button
                  onClick={() => {
                    onUpdateCheckpoint(cp.id, 'in_progress');
                    void onConfirmCheckpoint(cp.id, 'confirm');
                  }}
                  className="px-3 py-1 text-xs font-medium text-blue-600 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/40 rounded-lg transition-colors"
                >
                  Start
                </button>
              )}
              {cp.status === 'in_progress' && (
                <button
                  onClick={() => {
                    onUpdateCheckpoint(cp.id, 'completed');
                    void onConfirmCheckpoint(cp.id, 'confirm');
                  }}
                  className="px-3 py-1 text-xs font-medium text-green-600 bg-green-50 dark:bg-green-900/20 hover:bg-green-100 dark:hover:bg-green-900/40 rounded-lg transition-colors"
                >
                  Complete
                </button>
              )}
              {cp.status === 'completed' && (
                <span className="text-xs text-green-600 dark:text-green-400 font-medium">
                  Done
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Progress bar */}
      <div className="mt-6">
        <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
          <span>Progress</span>
          <span>{Math.round((checkpointList.filter(c => c.status === 'completed').length / checkpointList.length) * 100)}%</span>
        </div>
        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-blue-500 to-purple-600 transition-all duration-300"
            style={{ 
              width: `${(checkpointList.filter(c => c.status === 'completed').length / checkpointList.length) * 100}%` 
            }}
          />
        </div>
      </div>
    </div>
  );
}
