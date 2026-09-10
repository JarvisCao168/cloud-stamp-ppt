'use client';

import { useEffect, useRef } from 'react';
import { SlideData } from '@/types';

interface RevealInstance {
  on(event: string, callback: (event: { indexh: number }) => void): void;
  slide(index: number): void;
  destroy(): void;
}

interface RevealContainerProps {
  slides: SlideData[];
  activeSlide?: number;
  onSlideChange?: (index: number) => void;
}

export default function RevealContainer({ slides, activeSlide, onSlideChange }: RevealContainerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const revealInstance = useRef<RevealInstance | null>(null);

  useEffect(() => {
    if (!containerRef.current || !slides.length) return;

    // Import reveal.js dynamically to avoid SSR issues
    import('reveal.js').then((RevealModule) => {
      const R = RevealModule.default || RevealModule;
      
      if (revealInstance.current) {
        revealInstance.current.destroy();
      }

      // Ensure container exists before initializing
      if (containerRef.current) {
        revealInstance.current = new R(containerRef.current, {
          hash: true,
          slideNumber: 'c',
          showSlideNumber: 'all',
          transition: 'slide',
          transitionSpeed: 'default',
          backgroundTransition: 'fade',
        });

        revealInstance.current.on('slidechanged', (event) => {
          onSlideChange?.(event.indexh);
        });
      }
    });

    return () => {
      revealInstance.current?.destroy();
      revealInstance.current = null;
    };
  }, [slides.length, onSlideChange]);

  // Update slide when activeSlide changes externally
  useEffect(() => {
    if (revealInstance.current && activeSlide !== undefined) {
      revealInstance.current.slide(activeSlide);
    }
  }, [activeSlide]);

  if (!slides.length) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px] bg-gray-50 dark:bg-gray-900 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-700">
        <p className="text-gray-500 dark:text-gray-400 text-center p-8">
          生成演示文稿后将在此处预览
        </p>
      </div>
    );
  }

  return (
    <div className="reveal-container-wrapper w-full h-full min-h-[500px] bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
      <div ref={containerRef} className="reveal w-full h-full">
        <div className="slides">
          {slides.map((slide: SlideData, index: number) => (
            <section key={index} data-slide-id={`slide-${index}`}>
              <h2>{slide.title}</h2>
              <div className="content" style={{ textAlign: 'left', fontSize: '0.8em', padding: '20px' }}>
                {slide.content.split('\n').map((line: string, i: number) => (
                  <p key={i} style={{ marginBottom: '12px' }}>{line}</p>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
