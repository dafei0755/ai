'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { X, ExternalLink, ChevronLeft, ChevronRight, ZoomIn, Download } from 'lucide-react';

interface ImageResult {
  url: string;
  thumbnailUrl: string;
  title: string;
  sourceUrl: string;
  width: number;
  height: number;
}

interface ImageViewerProps {
  images: ImageResult[];
  initialIndex: number;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * 图片查看器组件
 *
 * 类似博查官网的图片浏览器：
 * - 左侧大图预览，支持鼠标滚轮翻页
 * - 右侧缩略图列表
 * - 顶部显示图片来源链接
 */
export default function ImageViewer({ images, initialIndex, isOpen, onClose }: ImageViewerProps) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [isLoading, setIsLoading] = useState(true);
  const [scale, setScale] = useState(1);
  const mainImageRef = useRef<HTMLDivElement>(null);
  const thumbnailListRef = useRef<HTMLDivElement>(null);

  // 当 initialIndex 变化时更新
  useEffect(() => {
    setCurrentIndex(initialIndex);
    setScale(1);
    setIsLoading(true);
  }, [initialIndex]);

  // 滚动到当前缩略图
  useEffect(() => {
    if (thumbnailListRef.current) {
      const thumbnails = thumbnailListRef.current.querySelectorAll('[data-thumbnail]');
      const currentThumbnail = thumbnails[currentIndex];
      if (currentThumbnail) {
        currentThumbnail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [currentIndex]);

  // 键盘事件处理
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          onClose();
          break;
        case 'ArrowLeft':
        case 'ArrowUp':
          navigatePrev();
          break;
        case 'ArrowRight':
        case 'ArrowDown':
          navigateNext();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, currentIndex]);

  // 鼠标滚轮翻页
  const handleWheel = useCallback((e: React.WheelEvent) => {
    // 防止页面滚动
    e.preventDefault();

    // 滚轮向下 = 下一张，向上 = 上一张
    if (e.deltaY > 0) {
      navigateNext();
    } else if (e.deltaY < 0) {
      navigatePrev();
    }
  }, [currentIndex, images.length]);

  // 导航到上一张
  const navigatePrev = useCallback(() => {
    setCurrentIndex(prev => (prev > 0 ? prev - 1 : images.length - 1));
    setIsLoading(true);
    setScale(1);
  }, [images.length]);

  // 导航到下一张
  const navigateNext = useCallback(() => {
    setCurrentIndex(prev => (prev < images.length - 1 ? prev + 1 : 0));
    setIsLoading(true);
    setScale(1);
  }, [images.length]);

  // 选择特定图片
  const selectImage = (index: number) => {
    setCurrentIndex(index);
    setIsLoading(true);
    setScale(1);
  };

  // 图片加载完成
  const handleImageLoad = () => {
    setIsLoading(false);
  };

  // 获取当前图片
  const currentImage = images[currentIndex];

  // 提取域名
  const getDomain = (url: string) => {
    try {
      return new URL(url).hostname;
    } catch {
      return '';
    }
  };

  if (!isOpen || !currentImage) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex bg-black/95"
      onClick={(e) => {
        // 点击背景关闭
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {/* 顶部工具栏 */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-4 py-3 bg-gradient-to-b from-black/80 to-transparent">
        {/* 图片来源链接 */}
        <a
          href={currentImage.sourceUrl || currentImage.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
          <span className="max-w-md truncate">{currentImage.sourceUrl || currentImage.url}</span>
        </a>

        {/* 右侧操作按钮 */}
        <div className="flex items-center gap-2">
          {/* 图片来源按钮 */}
          <a
            href={currentImage.sourceUrl || currentImage.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/80 hover:bg-blue-500 text-white text-sm transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            图片来源
          </a>

          {/* 关闭按钮 */}
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
          >
            <X className="w-5 h-5" />
            关闭
          </button>
        </div>
      </div>

      {/* 左侧：大图预览区 */}
      <div
        ref={mainImageRef}
        className="flex-1 flex items-center justify-center relative overflow-hidden"
        onWheel={handleWheel}
      >
        {/* 左箭头 */}
        <button
          onClick={navigatePrev}
          className="absolute left-4 z-10 p-3 rounded-full bg-black/50 hover:bg-black/70 text-white transition-colors"
        >
          <ChevronLeft className="w-6 h-6" />
        </button>

        {/* 大图 */}
        <div className="relative max-w-[calc(100%-320px)] max-h-[calc(100vh-120px)] flex items-center justify-center">
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-10 h-10 border-4 border-white/30 border-t-white rounded-full animate-spin" />
            </div>
          )}
          <img
            src={currentImage.url || currentImage.thumbnailUrl}
            alt={currentImage.title}
            className="max-w-full max-h-[calc(100vh-120px)] object-contain transition-transform duration-200"
            style={{ transform: `scale(${scale})` }}
            onLoad={handleImageLoad}
            draggable={false}
          />
        </div>

        {/* 右箭头 */}
        <button
          onClick={navigateNext}
          className="absolute right-[280px] z-10 p-3 rounded-full bg-black/50 hover:bg-black/70 text-white transition-colors"
        >
          <ChevronRight className="w-6 h-6" />
        </button>

        {/* 图片信息 */}
        <div className="absolute bottom-4 left-4 right-[280px] flex items-center justify-between">
          <div className="px-3 py-1.5 rounded-lg bg-black/50 text-white text-sm">
            <span className="font-medium">{currentIndex + 1}</span>
            <span className="text-white/60"> / {images.length}</span>
          </div>

          {currentImage.title && (
            <div className="px-3 py-1.5 rounded-lg bg-black/50 text-white text-sm max-w-md truncate">
              {currentImage.title}
            </div>
          )}

          {/* 滚轮提示 */}
          <div className="px-3 py-1.5 rounded-lg bg-black/50 text-white/60 text-xs">
            🖱️ 滚轮翻页
          </div>
        </div>
      </div>

      {/* 右侧：缩略图列表 */}
      <div className="w-[260px] bg-gray-900 border-l border-gray-800 flex flex-col">
        {/* 标题 */}
        <div className="px-4 py-3 border-b border-gray-800">
          <h3 className="text-white font-medium">图片列表</h3>
          <p className="text-gray-400 text-sm">{images.length} 张图片</p>
        </div>

        {/* 缩略图列表 - 可滚动 */}
        <div
          ref={thumbnailListRef}
          className="flex-1 overflow-y-auto p-2 space-y-2"
        >
          {images.map((image, index) => (
            <button
              key={index}
              data-thumbnail
              onClick={() => selectImage(index)}
              className={`
                relative w-full aspect-video rounded-lg overflow-hidden transition-all
                ${index === currentIndex
                  ? 'ring-2 ring-blue-500 ring-offset-2 ring-offset-gray-900'
                  : 'opacity-60 hover:opacity-100'}
              `}
            >
              <img
                src={image.thumbnailUrl || image.url}
                alt={image.title || `图片 ${index + 1}`}
                className="w-full h-full object-cover"
                loading="lazy"
              />

              {/* 编号 */}
              <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded bg-black/70 text-white text-xs">
                {index + 1}
              </div>

              {/* 当前选中标识 */}
              {index === currentIndex && (
                <div className="absolute inset-0 border-2 border-blue-500 rounded-lg" />
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
