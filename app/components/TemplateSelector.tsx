'use client';

import { useState, useEffect, useMemo } from 'react';
import { getAllAssets } from '@/api';

interface Template {
  id: string;
  name: string;
  category: string;
  preview: string;
  description?: string;
}

interface TemplateSelectorProps {
  value?: string;
  onChange?: (templateId: string) => void;
  disabled?: boolean;
  showDescription?: boolean;
}

export default function TemplateSelector({
  value,
  onChange,
  disabled = false,
  showDescription = false,
}: TemplateSelectorProps) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterCategory, setFilterCategory] = useState<string>('all');

  useEffect(() => {
    getAllAssets()
      .then((data) => {
        setTemplates(data.templates || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load templates:', err);
        setTemplates([]);
        setLoading(false);
      });
  }, []);

  const categories = useMemo(() => {
    const cats = new Set(templates.map((t) => t.category));
    return ['all', ...Array.from(cats)];
  }, [templates]);

  const filteredTemplates = useMemo(() => {
    if (filterCategory === 'all') return templates;
    return templates.filter((t) => t.category === filterCategory);
  }, [templates, filterCategory]);

  if (loading) {
    return (
      <div className="py-8 text-center text-gray-500 dark:text-gray-400">
        <div className="inline-flex items-center gap-2">
          <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          加载模板中...
        </div>
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* 分类筛选 */}
      <div className="flex flex-wrap gap-2 mb-4">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setFilterCategory(cat)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
              filterCategory === cat
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            {cat === 'all' ? '全部' : cat}
          </button>
        ))}
      </div>

      {/* 模板网格 */}
      {filteredTemplates.length === 0 ? (
        <div className="py-8 text-center text-gray-400 dark:text-gray-500">
          暂无模板
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTemplates.map((template) => (
            <div
              key={template.id}
              onClick={() => !disabled && onChange?.(template.id)}
              className={`
                rounded-xl border-2 cursor-pointer transition-all duration-200
                ${
                  value === template.id
                    ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20 shadow-md'
                    : disabled
                    ? 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 cursor-not-allowed opacity-60'
                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-400 hover:shadow-md'
                }
              `}
            >
              {/* 预览区域 */}
              <div className="aspect-video bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 rounded-t-xl flex items-center justify-center overflow-hidden">
                {template.preview ? (
                  <img
                    src={template.preview}
                    alt={template.name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                      (e.target as HTMLImageElement).parentElement!.innerHTML =
                        `<span class="text-3xl">${getTemplateEmoji(template.id)}</span>`;
                    }}
                  />
                ) : (
                  <span className="text-3xl">{getTemplateEmoji(template.id)}</span>
                )}
              </div>

              {/* 信息区域 */}
              <div className="p-3">
                <div className="flex items-center justify-between">
                  <p className="font-medium text-gray-900 dark:text-white text-sm truncate">
                    {template.name}
                  </p>
                  {value === template.id && (
                    <svg className="w-5 h-5 text-blue-600 flex-shrink-0 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  {template.category}
                </p>
                {showDescription && template.description && (
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-2 line-clamp-2">
                    {template.description}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 已选提示 */}
      {value && (
        <p className="mt-3 text-sm text-blue-600 dark:text-blue-400">
          已选择: {templates.find((t) => t.id === value)?.name}
        </p>
      )}
    </div>
  );
}

function getTemplateEmoji(id: string): string {
  const emojiMap: Record<string, string> = {
    'modern-dark': '🌑',
    'corporate-clean': '💼',
    'futuristic-neon': '⚡',
    'minimal-light': '☀️',
    'nature-organic': '🌿',
    'academic': '📚',
  };
  return emojiMap[id] || '📊';
}
