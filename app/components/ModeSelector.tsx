'use client';

import { PresentationMode } from '@/types';
import { MODE_CONFIG } from '../machine';

interface ModeSelectorProps {
  currentMode: PresentationMode;
  onModeChange: (mode: PresentationMode) => void;
}

export default function ModeSelector({ currentMode, onModeChange }: ModeSelectorProps) {
  return (
    <div className="flex flex-wrap gap-3 justify-center">
      {(Object.keys(MODE_CONFIG) as PresentationMode[]).map((mode) => {
        const config = MODE_CONFIG[mode];
        const isActive = mode === currentMode;
        
        return (
          <button
            key={mode}
            onClick={() => onModeChange(mode)}
            className={`
              relative flex flex-col items-center px-6 py-4 rounded-xl
              transition-all duration-200 ease-in-out
              ${isActive 
                ? 'bg-white dark:bg-gray-800 shadow-lg scale-105 ring-2 ring-offset-2 ring-current' 
                : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'
              }
              ${isActive ? 'text-gray-900 dark:text-white' : 'text-gray-600 dark:text-gray-400'}
            `}
            aria-pressed={isActive}
            aria-label={`选择${config.label}模式`}
          >
            {/* Mode color indicator */}
            <div 
              className={`absolute -top-1 -right-1 w-3 h-3 rounded-full bg-gradient-to-br ${config.color}`}
              aria-hidden="true"
            />
            
            {/* Icon */}
            <span className="text-2xl mb-2" aria-hidden="true">
              {config.icon}
            </span>
            
            {/* Label */}
            <span className="font-semibold text-sm">{config.label}</span>
            
            {/* Description */}
            <span className="text-xs mt-1 opacity-75">{config.description}</span>
          </button>
        );
      })}
    </div>
  );
}
