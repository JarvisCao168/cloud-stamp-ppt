"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { NumberingStyle, NUMBERING_TYPE_LABELS } from '@/data/numberingStyles';
import { getNumberingStyles } from '@/api';

interface NumberingSelectorProps {
  value?: string;
  onChange?: (styleId: string) => void;
  disabled?: boolean;
  showPreview?: boolean;
}

const NumberingSelector: React.FC<NumberingSelectorProps> = ({
  value,
  onChange,
  disabled = false,
  showPreview = true,
}) => {
  const [styles, setStyles] = useState<NumberingStyle[]>([]);
  const [filterType, setFilterType] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 从后端 API 加载序号样式数据
    getNumberingStyles()
      .then((data) => {
        setStyles(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load numbering styles:', err);
        // 降级到本地数据
        import('@/data/numberingStyles').then((mod) => {
          setStyles(mod.NUMBERING_STYLES);
          setLoading(false);
        });
      });
  }, []);

  const filteredStyles = useMemo(() => {
    if (filterType === 'all') return styles;
    return styles.filter(s => s.type === filterType);
  }, [styles, filterType]);

  const handleSelect = (styleId: string) => {
    onChange?.(styleId);
  };

  if (loading) {
    return <div className="py-4 text-center text-gray-500">加载中...</div>;
  }

  return (
    <div className="w-full">
      {/* 类型筛选 */}
      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => setFilterType('all')}
          className={`px-3 py-1 rounded-full text-sm transition-colors ${
            filterType === 'all'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          全部
        </button>
        {Object.entries(NUMBERING_TYPE_LABELS).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilterType(key)}
            className={`px-3 py-1 rounded-full text-sm transition-colors ${
              filterType === key
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 样式网格 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {filteredStyles.map((style) => (
          <div
            key={style.id}
            onClick={() => !disabled && handleSelect(style.id)}
            className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
              value === style.id
                ? 'border-blue-600 bg-blue-50'
                : disabled
                ? 'border-gray-200 bg-gray-50 cursor-not-allowed'
                : 'border-gray-200 hover:border-blue-400 hover:bg-gray-50'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-gray-800">{style.name}</span>
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                {NUMBERING_TYPE_LABELS[style.type]}
              </span>
            </div>
            
            {/* 符号预览 */}
            <div className="flex flex-wrap gap-1 mb-2 font-mono text-lg">
              {style.symbols.slice(0, 5).map((sym, idx) => (
                <span key={idx} className="text-gray-700">{sym}</span>
              ))}
              {style.symbols.length > 5 && (
                <span className="text-gray-400 text-sm">...</span>
              )}
            </div>

            {/* 描述 */}
            <p className="text-xs text-gray-500 line-clamp-1">{style.description}</p>
            
            {/* 标签 */}
            <div className="flex flex-wrap gap-1 mt-2">
              {style.tags.slice(0, 3).map((tag) => (
                <span key={tag} className="text-xs text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* 详细预览 */}
      {showPreview && value && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm font-medium text-gray-700 mb-2">选中样式预览：</p>
          <div 
            className="text-gray-800"
            dangerouslySetInnerHTML={{ __html: styles.find(s => s.id === value)?.preview_html || '' }}
          />
        </div>
      )}
    </div>
  );
};

export default NumberingSelector;
