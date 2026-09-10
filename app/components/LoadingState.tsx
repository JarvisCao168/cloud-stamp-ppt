import React from 'react';

interface LoadingStateProps {
  message?: string;
}

export default function LoadingState({ message = '正在生成演示文稿...' }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-8">
      {/* Animated spinner */}
      <div className="relative w-16 h-16 mb-6">
        <div className="absolute inset-0 rounded-full border-4 border-gray-200 dark:border-gray-700" />
        <div 
          className="absolute inset-0 rounded-full border-4 border-t-blue-500 border-r-transparent border-b-transparent border-l-transparent animate-spin"
          aria-hidden="true"
        />
      </div>
      
      <p className="text-gray-600 dark:text-gray-400 text-center font-medium">
        {message}
      </p>
      
      <p className="text-gray-400 dark:text-gray-500 text-sm mt-2">
        请稍候，正在为您创建内容...
      </p>
    </div>
  );
}
