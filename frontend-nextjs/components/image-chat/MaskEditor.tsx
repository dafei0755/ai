/**
 * 🔥 v7.62: Mask 编辑器组件
 * 
 * 功能：
 * - 显示原始图片作为背景
 * - Canvas 覆盖层用于绘制 Mask
 * - 画笔工具（黑色，可调节大小）
 * - 橡皮擦工具（透明）
 * - 清空 Mask
 * - 导出 Mask 为 PNG Base64（黑色=保留，透明=编辑区域）
 */
'use client';

import React, { useRef, useEffect, useState } from 'react';
import { Paintbrush, Eraser, Trash2, Eye, EyeOff, Download } from 'lucide-react';

interface MaskEditorProps {
  imageUrl: string;  // 原始图片 URL
  onMaskChange: (maskBase64: string | null) => void;  // Mask 变化回调
}

export default function MaskEditor({ imageUrl, onMaskChange }: MaskEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  
  const [isDrawing, setIsDrawing] = useState(false);
  const [tool, setTool] = useState<'brush' | 'eraser'>('brush');
  const [brushSize, setBrushSize] = useState(30);
  const [showMask, setShowMask] = useState(true);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 });

  // 初始化 Canvas
  useEffect(() => {
    if (!imageUrl || !imageLoaded) return;

    const img = imageRef.current;
    const canvas = canvasRef.current;
    if (!img || !canvas) return;

    // 设置 Canvas 尺寸与图片相同
    const rect = img.getBoundingClientRect();
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    
    setCanvasSize({ width: img.naturalWidth, height: img.naturalHeight });

    // 初始化为完全透明（全部可编辑）
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    // 触发初始 Mask 导出（空 Mask）
    exportMask();
  }, [imageUrl, imageLoaded]);

  // 图片加载完成
  const handleImageLoad = () => {
    setImageLoaded(true);
  };

  // 获取 Canvas 坐标
  const getCanvasCoordinates = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return null;

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  };

  // 开始绘制
  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDrawing(true);
    draw(e);
  };

  // 绘制
  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing && e.type !== 'mousedown') return;

    const coords = getCanvasCoordinates(e);
    if (!coords) return;

    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!ctx) return;

    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = brushSize;

    if (tool === 'brush') {
      // 画笔：黑色（保留区域）
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = 'black';
    } else {
      // 橡皮擦：透明（编辑区域）
      ctx.globalCompositeOperation = 'destination-out';
    }

    ctx.lineTo(coords.x, coords.y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(coords.x, coords.y);
  };

  // 停止绘制
  const stopDrawing = () => {
    if (!isDrawing) return;
    setIsDrawing(false);
    
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (ctx) {
      ctx.beginPath();
    }

    // 导出 Mask
    exportMask();
  };

  // 清空 Mask
  const clearMask = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (ctx && canvas) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    onMaskChange(null);
  };

  // 导出 Mask 为 Base64
  const exportMask = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    try {
      // 导出为 PNG（保留透明度）
      const maskBase64 = canvas.toDataURL('image/png');
      onMaskChange(maskBase64);
    } catch (error) {
      console.error('导出 Mask 失败:', error);
      onMaskChange(null);
    }
  };

  // 下载 Mask（调试用）
  const downloadMask = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const link = document.createElement('a');
    link.download = `mask-${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  return (
    <div className="border border-white/10 rounded-lg overflow-hidden bg-black/50">
      {/* 工具栏 */}
      <div className="p-3 bg-black/70 border-b border-white/10">
        <div className="flex items-center justify-between gap-3">
          {/* 工具选择 */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTool('brush')}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                tool === 'brush'
                  ? 'bg-blue-500/30 border border-blue-500/50 text-blue-300'
                  : 'bg-white/5 border border-white/10 text-white/50 hover:bg-white/10'
              }`}
            >
              <Paintbrush className="w-4 h-4" />
              <span>画笔</span>
            </button>
            <button
              onClick={() => setTool('eraser')}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                tool === 'eraser'
                  ? 'bg-amber-500/30 border border-amber-500/50 text-amber-300'
                  : 'bg-white/5 border border-white/10 text-white/50 hover:bg-white/10'
              }`}
            >
              <Eraser className="w-4 h-4" />
              <span>橡皮擦</span>
            </button>
          </div>

          {/* 画笔大小 */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-white/50">大小</span>
            <input
              type="range"
              min="5"
              max="80"
              value={brushSize}
              onChange={(e) => setBrushSize(Number(e.target.value))}
              className="w-24"
            />
            <span className="text-xs text-white/70 w-8">{brushSize}px</span>
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowMask(!showMask)}
              className="p-2 bg-white/5 border border-white/10 rounded-lg text-white/70 hover:bg-white/10 transition-colors"
              title={showMask ? '隐藏蒙版' : '显示蒙版'}
            >
              {showMask ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            </button>
            <button
              onClick={downloadMask}
              className="p-2 bg-white/5 border border-white/10 rounded-lg text-white/70 hover:bg-white/10 transition-colors"
              title="下载 Mask"
            >
              <Download className="w-4 h-4" />
            </button>
            <button
              onClick={clearMask}
              className="flex items-center gap-2 px-3 py-2 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 hover:bg-red-500/30 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              <span className="text-sm">清空</span>
            </button>
          </div>
        </div>

        {/* 提示说明 */}
        <div className="mt-3 pt-3 border-t border-white/5 text-xs text-white/40">
          <p>💡 <strong className="text-white/60">黑色区域</strong> = 保留不变 · <strong className="text-white/60">透明区域</strong> = 生成编辑</p>
          <p className="mt-1">建议：先用画笔画出要<strong className="text-amber-400">保留</strong>的区域，剩余透明部分将被 AI 编辑</p>
        </div>
      </div>

      {/* Canvas 编辑区 */}
      <div className="relative bg-gray-900 flex items-center justify-center min-h-[400px]">
        {/* 原始图片 */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          ref={imageRef}
          src={imageUrl}
          alt="原始图片"
          onLoad={handleImageLoad}
          className="max-w-full max-h-[600px] object-contain"
          style={{ display: imageLoaded ? 'block' : 'none' }}
        />

        {/* Mask Canvas 覆盖层 */}
        {imageLoaded && (
          <canvas
            ref={canvasRef}
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            className="absolute top-0 left-0 cursor-crosshair"
            style={{
              width: imageRef.current?.clientWidth || 0,
              height: imageRef.current?.clientHeight || 0,
              opacity: showMask ? 0.7 : 0,
              mixBlendMode: 'multiply'
            }}
          />
        )}

        {/* 加载提示 */}
        {!imageLoaded && (
          <div className="text-white/50 text-sm">加载图片中...</div>
        )}
      </div>

      {/* 底部信息 */}
      {imageLoaded && (
        <div className="p-2 bg-black/70 border-t border-white/10 text-xs text-white/40 text-center">
          图片尺寸: {canvasSize.width} × {canvasSize.height} · 
          当前工具: {tool === 'brush' ? '画笔（保留）' : '橡皮擦（编辑）'} · 
          大小: {brushSize}px
        </div>
      )}
    </div>
  );
}
