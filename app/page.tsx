'use client';

import { useState } from 'react';
import ModeSelector from './components/ModeSelector';
import TemplateSelector from './components/TemplateSelector';
import NumberingSelector from './components/NumberingSelector';
import RevealContainer from './components/RevealContainer';
import CheckpointPanel from './components/CheckpointPanel';
import LoadingState from './components/LoadingState';
import ErrorMessage from './components/ErrorMessage';
import { useGeneration } from './generationStore';
import { MODE_CONFIG } from './machine';
import { exportPresentationToFile, EXPORT_FORMATS } from './export';

export default function Home() {
  const {
    mode, state, prompt, setPrompt, updateMode,
    generate, reset, checkpoints, updateCheckpoint, confirmCheckpoint,
    sessionId, options, updateOptions, numberingStyles,
  } = useGeneration();
  const [activeSlide, setActiveSlide] = useState(0);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [showTemplateSelector, setShowTemplateSelector] = useState(false);
  const [showNumberingSelector, setShowNumberingSelector] = useState(false);

  // 获取已选模板名称用于显示
  const selectedTemplateName = options.templateId
    ? options.templateId
    : '未选择模板';

  const currentModeConfig = MODE_CONFIG[mode];

  const handleGenerate = () => {
    generate();
    setActiveSlide(0);
  };

  const handleSlideChange = (index: number) => {
    setActiveSlide(index);
  };

  const handleExport = async (format: string) => {
    if (!sessionId) return;
    setExportingFormat(format);
    setExportError(null);
    try {
      const numberingStyleId = options.numberingStyleId
        ? options.numberingStyleId
        : undefined;
      await exportPresentationToFile(
        state.slides || [],
        { format: format as 'pptx' | 'pdf' | 'png' | 'html', numberingStyleId },
        sessionId
      );
    } catch (err) {
      setExportError(err instanceof Error ? err.message : '导出失败');
    } finally {
      setExportingFormat(null);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">AI</span>
            </div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
              演示文稿生成器
            </h1>
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            当前模式: <span className="font-medium text-gray-700 dark:text-gray-300">{currentModeConfig.label}</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-6">

          {/* Input Section */}
          <section className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              创建演示文稿
            </h2>

            {/* Mode Selector */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                选择模式
              </label>
              <ModeSelector currentMode={mode} onModeChange={updateMode} />
            </div>

            {/* Prompt Input */}
            <div className="space-y-3">
              <div>
                <label
                  htmlFor="prompt"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                >
                  请输入主题或内容描述
                </label>
                <textarea
                  id="prompt"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder={`例如：人工智能的发展趋势、项目进展汇报、产品发布演示...`}
                  rows={4}
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none transition-colors"
                  aria-describedby="prompt-help"
                />
                <p id="prompt-help" className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  描述您想要创建的演示文稿内容，AI 将自动生成幻灯片
                </p>
              </div>

              {/* 保持原文模式开关 */}
              <div className="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => updateOptions({ keepOriginal: !options.keepOriginal })}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    options.keepOriginal
                      ? 'bg-blue-600'
                      : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                  aria-pressed={options.keepOriginal}
                  aria-label="切换保持原文模式"
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      options.keepOriginal ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
                <div>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    保持原文模式
                  </span>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {options.keepOriginal
                      ? 'AI仅作排版，不改写原文内容'
                      : '禁用：AI将根据主题生成内容'}
                  </p>
                </div>
              </div>

              {/* 模板与序号样式选择（仅掌控模式显示） */}
              {mode === 'mastery' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div>
                    <button
                      type="button"
                      onClick={() => {
                        setShowTemplateSelector(!showTemplateSelector);
                        if (showNumberingSelector) setShowNumberingSelector(false);
                      }}
                      className="w-full flex items-center justify-between px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-left hover:border-blue-500 transition-colors"
                    >
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        {options.templateId
                          ? `已选模板: ${options.templateId}`
                          : '选择模板 (可选)'}
                      </span>
                      <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    {showTemplateSelector && (
                      <div className="mt-2 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                        <TemplateSelector
                          value={options.templateId}
                          onChange={(id) => {
                            updateOptions({ templateId: id });
                            // 自动关联推荐的序号样式
                            const autoNumbering: Record<string, string> = {
                              'modern-dark': 'numeric-dot',
                              'corporate-clean': 'numeric-dot',
                              'futuristic-neon': 'icon-arrow',
                              'minimal-light': 'chinese-clause',
                              'nature-organic': 'graphic-bullet',
                              'academic': 'chinese-paren',
                            };
                            const recommended = autoNumbering[id];
                            if (recommended && !options.numberingStyleId) {
                              updateOptions({ numberingStyleId: recommended });
                            }
                          }}
                          showDescription
                        />
                      </div>
                    )}
                  </div>

                  <div>
                    <button
                      type="button"
                      onClick={() => {
                        setShowNumberingSelector(!showNumberingSelector);
                        if (showTemplateSelector) setShowTemplateSelector(false);
                      }}
                      className="w-full flex items-center justify-between px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-left hover:border-blue-500 transition-colors"
                    >
                      <span className="text-sm text-gray-700 dark:text-gray-300">
                        {options.numberingStyleId
                          ? `已选序号: ${options.numberingStyleId}`
                          : '选择序号样式 (可选)'}
                      </span>
                      <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    {showNumberingSelector && (
                      <div className="mt-2 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                        <NumberingSelector
                          value={options.numberingStyleId}
                          onChange={(id) => updateOptions({ numberingStyleId: id })}
                        />
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={handleGenerate}
                  disabled={state.status === 'loading'}
                  className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg"
                  aria-label="生成演示文稿"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                  生成演示文稿
                </button>

                {state.status === 'success' && (
                  <button
                    onClick={reset}
                    className="flex items-center gap-2 px-6 py-2.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-lg transition-colors"
                    aria-label="重新生成"
                  >
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                      />
                    </svg>
                    重新生成
                  </button>
                )}
              </div>
            </div>
          </section>

          {/* Checkpoint Panel (mastery mode only) */}
          {mode === 'mastery' && checkpoints.size > 0 && (
            <CheckpointPanel
              checkpoints={checkpoints}
              onUpdateCheckpoint={updateCheckpoint}
              onConfirmCheckpoint={confirmCheckpoint}
              mode={mode}
            />
          )}

          {/* Preview Section */}
          <section
            className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6"
            aria-label="预览区域"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-gray-900 dark:text-white">
                预览
              </h2>
              {state.status === 'success' && state.slides && (
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {activeSlide + 1} / {state.slides.length} 页
                </span>
              )}
            </div>

            <div className="aspect-video w-full">
              {state.status === 'loading' && (
                <LoadingState />
              )}

              {state.status === 'error' && (
                <ErrorMessage
                  message={state.error || '生成失败'}
                  onRetry={handleGenerate}
                />
              )}

              {state.status === 'success' && state.slides && (
                <RevealContainer
                  slides={state.slides}
                  activeSlide={activeSlide}
                  onSlideChange={handleSlideChange}
                />
              )}

              {state.status === 'idle' && (
                <div className="flex items-center justify-center h-full min-h-[400px] bg-gray-50 dark:bg-gray-900 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-700">
                  <div className="text-center p-8">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                      <svg
                        className="w-8 h-8 text-gray-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                        />
                      </svg>
                    </div>
                    <p className="text-gray-500 dark:text-gray-400 font-medium">
                      输入主题后点击生成
                    </p>
                    <p className="text-gray-400 dark:text-gray-500 text-sm mt-1">
                      演示文稿将在此处显示
                    </p>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Export Section */}
          {state.status === 'success' && sessionId && (
            <section
              className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6"
              aria-label="导出区域"
            >
              <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                导出演示文稿
              </h2>

              {exportError && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm" role="alert">
                  {exportError}
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                {EXPORT_FORMATS.map((format) => (
                  <button
                    key={format.type}
                    onClick={() => handleExport(format.type)}
                    disabled={exportingFormat !== null}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label={`导出为 ${format.name}`}
                  >
                    {exportingFormat === format.type ? (
                      <>
                        <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        导出中...
                      </>
                    ) : (
                      <>
                        <span>{format.icon}</span>
                        {format.name}
                      </>
                    )}
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* Tips Section */}
          <section className="bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800 p-4">
            <div className="flex items-start gap-3">
              <svg
                className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div>
                <h3 className="font-medium text-blue-900 dark:text-blue-300">使用提示</h3>
                <ul className="mt-2 text-sm text-blue-800 dark:text-blue-400 space-y-1">
                  <li>• <strong>极速模式</strong>：适合快速生成简洁的演示文稿</li>
                  <li>• <strong>协作模式</strong>：适合团队协作和项目展示</li>
                  <li>• <strong>掌控模式</strong>：提供详细的内容和完整的结构</li>
                  <li>• 使用方向键或空格键在幻灯片间导航</li>
                  <li>• 连接后端服务后可导出 PPTX/PDF 格式</li>
                  <li>• <strong>保持原文模式</strong>：直接将上传内容按段落分页，不做AI改写（参考即触AI）</li>
                </ul>
              </div>
            </div>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 px-4 py-4">
        <div className="max-w-7xl mx-auto text-center text-sm text-gray-500 dark:text-gray-400">
          <p>AI 演示文稿生成器 • 使用 Reveal.js 渲染</p>
        </div>
      </footer>
    </div>
  );
}
