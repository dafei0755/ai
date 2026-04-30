/**
 * 🔥 独立的图片查看器组件
 *
 * 用于专家报告中的概念图查看
 * - 纯查看模式（缩放、下载）
 * - 深度思考模式显示"进入对话模式"按钮
 * - ESC 键关闭
 */
'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { X, Download, MessageCircle } from 'lucide-react';
import type { ExpertGeneratedImage } from '@/types';

interface ImageViewerProps {
  image: ExpertGeneratedImage;
  expertName: string;
  sessionId: string;
  analysisMode: 'normal' | 'deep_thinking';
  onClose: () => void;
  onEnterChat?: () => void;  // 仅 deep_thinking 模式需要
}

export default function ImageViewer({
  image,
  expertName,
  sessionId,
  analysisMode,
  onClose,
  onEnterChat
}: ImageViewerProps) {
  const [zoomLevel, setZoomLevel] = useState(1);

  // 滚轮缩放
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoomLevel(prev => Math.max(0.5, Math.min(3, prev + delta)));
  }, []);

  // 下载图片
  const handleDownload = () => {
    if (!image.image_url) return;
    const link = document.createElement('a');
    link.href = image.image_url;
    link.download = `${expertName}-concept-${Date.now()}.png`;
    link.click();
  };

  // ESC 键关闭
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-sm flex items-center justify-center">
      {/* 顶部操作栏 */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-4 py-3 bg-gradient-to-b from-black/80 to-transparent">
        <div className="text-sm text-white/90 font-medium">
          {expertName} - 概念图
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            title="下载图片"
          >
            <Download className="w-5 h-5 text-white/70 hover:text-white" />
          </button>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            title="关闭"
          >
            <X className="w-5 h-5 text-white/70 hover:text-white" />
          </button>
        </div>
      </div>

      {/* 图像区域 */}
      <div
        className="max-w-[90vw] max-h-[80vh] overflow-hidden cursor-zoom-in"
        onWheel={handleWheel}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={image.image_url}
          alt={image.prompt || '概念图'}
          className="max-w-full max-h-[80vh] object-contain transition-transform duration-200"
          style={{ transform: `scale(${zoomLevel})` }}
        />
      </div>

      {/* 底部操作栏 */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2">
        {/* 缩放提示 */}
        <div className="px-4 py-2 bg-black/60 rounded-full text-sm text-white/70">
          滚轮缩放 · 当前 {Math.round(zoomLevel * 100)}%
        </div>

        {/* 🔥 关键：仅深度思考模式显示对话链接 */}
        {analysisMode === 'deep_thinking' && onEnterChat && (
          <button
            onClick={onEnterChat}
            className="px-6 py-2.5 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/50 rounded-full text-sm text-blue-300 hover:text-blue-200 transition-all flex items-center gap-2"
          >
            <MessageCircle className="w-4 h-4" />
            进入对话模式
          </button>
        )}
      </div>
    </div>
  );
}
