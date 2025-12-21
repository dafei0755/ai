/**
 * 🔥 v7.48: 图片生成对话窗口
 * 
 * 类似 Google AI Studio 的连续对话界面
 * - 上部：对话历史（用户请求 + AI响应图片）
 * - 下部：输入区（提示词 + 参考图上传 + 比例/风格选择）
 * - 点击图片进入纯查看模式
 * - 悬停显示删除按钮
 * - 支持多轮对话上下文传递
 */
'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  X, Send, Upload, Image as ImageIcon, Trash2, Download,
  Loader2, Sparkles, ChevronDown, AlertCircle, Maximize2
} from 'lucide-react';
import { api } from '@/lib/api';
import type {
  ExpertGeneratedImage,
  ImageChatTurn,
  ImageChatHistory,
  AspectRatio,
  StyleType,
  SuggestedPrompt
} from '@/types';
import MaskEditor from './MaskEditor';  // 🔥 v7.62: Mask 编辑器

// ==================== Props ====================
interface ImageChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  expertName: string;
  sessionId: string;
  initialImages?: ExpertGeneratedImage[];
  initialImage?: ExpertGeneratedImage | null;  // 🔥 v7.48: 支持单图初始化
  onImagesUpdated?: (images: ExpertGeneratedImage[]) => void;
  onImageUpdate?: (expertName: string, newImage: ExpertGeneratedImage) => void;  // 🔥 v7.48: 单图更新回调
}

// ==================== 常量 ====================
const ASPECT_RATIO_OPTIONS: { value: AspectRatio; label: string; icon: string }[] = [
  { value: '16:9', label: '横幅 16:9', icon: '▬' },
  { value: '1:1', label: '方形 1:1', icon: '◼' },
  { value: '9:16', label: '纵幅 9:16', icon: '▮' },
  { value: '4:3', label: '标准 4:3', icon: '▭' },
  { value: '21:9', label: '超宽 21:9', icon: '━' },
];

const STYLE_TYPE_OPTIONS: { value: StyleType; label: string }[] = [
  { value: 'interior', label: '室内设计' },
  { value: 'architecture', label: '建筑设计' },
  { value: 'product', label: '产品设计' },
  { value: 'branding', label: '品牌视觉' },
  { value: 'conceptual', label: '概念艺术' },
];

// ==================== 主组件 ====================
export default function ImageChatModal({
  isOpen,
  onClose,
  expertName,
  sessionId,
  initialImages = [],
  initialImage = null,  // 🔥 v7.48: 支持单图初始化
  onImagesUpdated,
  onImageUpdate  // 🔥 v7.48: 单图更新回调
}: ImageChatModalProps) {
  // 🔥 v7.48: 合并初始图片
  const mergedInitialImages = React.useMemo(() => {
    const images = [...initialImages];
    if (initialImage && !images.find(img => img.id === initialImage.id)) {
      images.unshift(initialImage);
    }
    return images;
  }, [initialImages, initialImage]);

  // 对话历史
  const [chatHistory, setChatHistory] = useState<ImageChatTurn[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  
  // 输入状态
  const [prompt, setPrompt] = useState('');
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('16:9');
  const [styleType, setStyleType] = useState<StyleType>('interior');
  const [referenceImage, setReferenceImage] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  
  // 🔥 v7.61: Vision 图像分析状态
  const [useVisionAnalysis, setUseVisionAnalysis] = useState(true);
  const [visionFocus, setVisionFocus] = useState<'comprehensive' | 'style' | 'composition' | 'colors'>('comprehensive');
  const [isAnalyzingVision, setIsAnalyzingVision] = useState(false);
  
  // 🔥 v7.62: Inpainting 编辑模式状态
  const [editMode, setEditMode] = useState(false);
  const [maskData, setMaskData] = useState<string | null>(null);
  
  // 下拉菜单状态
  const [showAspectDropdown, setShowAspectDropdown] = useState(false);
  const [showStyleDropdown, setShowStyleDropdown] = useState(false);
  
  // 智能推荐
  const [suggestedPrompts, setSuggestedPrompts] = useState<SuggestedPrompt[]>([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  
  // 图片查看器
  const [viewingImage, setViewingImage] = useState<ExpertGeneratedImage | null>(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  
  // Refs
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageContainerRef = useRef<HTMLDivElement>(null);

  // ==================== 加载对话历史 ====================
  useEffect(() => {
    if (isOpen && sessionId && expertName) {
      loadChatHistory();
      loadSuggestedPrompts();
    }
  }, [isOpen, sessionId, expertName]);

  const loadChatHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const response = await api.getImageChatHistory(sessionId, expertName);
      if (response.success && response.history) {
        // 🔥 v7.48: 类型转换
        const turns = (response.history.turns || []).map((turn: Record<string, unknown>) => ({
          ...turn,
          aspect_ratio: turn.aspect_ratio as AspectRatio | undefined,
          style_type: turn.style_type as StyleType | undefined,
        })) as ImageChatTurn[];

        // 如果成功返回但历史为空，仍要用初始图片填充，避免空白界面
        if (turns.length > 0) {
          setChatHistory(turns);
        } else {
          const initialTurns: ImageChatTurn[] = mergedInitialImages.map((img, idx) => ({
            turn_id: img.id || `initial-${idx}`,
            type: 'assistant' as const,
            timestamp: img.created_at || new Date().toISOString(),
            image: img
          }));
          setChatHistory(initialTurns);
        }
      } else {
        // 如果没有历史，从初始图片构建
        const initialTurns: ImageChatTurn[] = mergedInitialImages.map((img, idx) => ({
          turn_id: img.id || `initial-${idx}`,
          type: 'assistant' as const,
          timestamp: img.created_at || new Date().toISOString(),
          image: img
        }));
        setChatHistory(initialTurns);
      }
    } catch (error) {
      console.error('加载对话历史失败:', error);
      // 回退到初始图片
      const initialTurns: ImageChatTurn[] = mergedInitialImages.map((img, idx) => ({
        turn_id: img.id || `initial-${idx}`,
        type: 'assistant' as const,
        timestamp: img.created_at || new Date().toISOString(),
        image: img
      }));
      setChatHistory(initialTurns);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const loadSuggestedPrompts = async () => {
    setIsLoadingSuggestions(true);
    try {
      const response = await api.suggestImagePrompts(sessionId, expertName);
      if (response.success) {
        setSuggestedPrompts(response.suggestions || []);
      }
    } catch (error) {
      console.error('加载推荐提示词失败:', error);
    } finally {
      setIsLoadingSuggestions(false);
    }
  };

  // ==================== 滚动到底部 ====================
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory]);

  // ==================== 发送消息 ====================
  const handleSend = async () => {
    if (!prompt.trim() || isGenerating) return;

    const userTurn: ImageChatTurn = {
      turn_id: `user-${Date.now()}`,
      type: 'user',
      timestamp: new Date().toISOString(),
      prompt: prompt.trim(),
      aspect_ratio: aspectRatio,
      style_type: styleType,
      reference_image_url: referenceImage || undefined
    };

    // 添加用户消息和加载中的AI响应
    const loadingTurn: ImageChatTurn = {
      turn_id: `loading-${Date.now()}`,
      type: 'assistant',
      timestamp: new Date().toISOString(),
      isLoading: true
    };

    setChatHistory(prev => [...prev, userTurn, loadingTurn]);
    setPrompt('');
    setReferenceImage(null);
    setIsGenerating(true);

    try {
      // 构建上下文（之前的对话）
      const context = chatHistory
        .filter(t => t.type === 'user' && t.prompt)
        .map(t => t.prompt)
        .join('\n');

      // 🔥 v7.62: 根据模式选择参数
      const requestParams: any = {
        prompt: prompt.trim(),
        aspect_ratio: aspectRatio,
        style_type: styleType,
        reference_image: referenceImage || undefined,
        context: context || undefined
      };
      
      // 编辑模式：添加 Mask 参数
      if (editMode && maskData && referenceImage) {
        requestParams.mask_image = maskData;
        requestParams.edit_mode = true;
      } else if (referenceImage) {
        // 生成模式：添加 Vision 分析参数
        requestParams.use_vision_analysis = useVisionAnalysis;
        requestParams.vision_focus = visionFocus;
      }
      
      const result = await api.regenerateImageWithContext(sessionId, expertName, requestParams);

      // 替换加载中的消息为实际结果
      setChatHistory(prev => {
        const newHistory = prev.filter(t => !t.isLoading);
        if (result.success && result.image_url) {
          const assistantTurn: ImageChatTurn = {
            turn_id: result.image_id || `img-${Date.now()}`,
            type: 'assistant',
            timestamp: new Date().toISOString(),
            image: {
              expert_name: expertName,
              image_url: result.image_url,
              prompt: prompt.trim(),
              prompt_used: prompt.trim(),
              id: result.image_id,
              aspect_ratio: aspectRatio,
              style_type: styleType,
              created_at: new Date().toISOString()
            }
          };
          return [...newHistory, assistantTurn];
        } else {
          const errorTurn: ImageChatTurn = {
            turn_id: `error-${Date.now()}`,
            type: 'assistant',
            timestamp: new Date().toISOString(),
            error: result.error || '图片生成失败，请重试'
          };
          return [...newHistory, errorTurn];
        }
      });

      // 保存对话历史到后端
      await saveChatHistory();

      // 🔥 v7.48: 通知父组件更新单张图片（用于 ExpertReportAccordion 场景）
      if (result.success && result.image_url && onImageUpdate) {
        const newImage: ExpertGeneratedImage = {
          expert_name: expertName,
          image_url: result.image_url,
          prompt: prompt.trim(),
          prompt_used: prompt.trim(),
          id: result.image_id,
          aspect_ratio: aspectRatio,
          style_type: styleType,
          created_at: new Date().toISOString()
        };
        onImageUpdate(expertName, newImage);
      }

      // 通知父组件更新图片列表（用于批量更新场景）
      if (result.success && onImagesUpdated) {
        const allImages = chatHistory
          .filter(t => t.type === 'assistant' && t.image)
          .map(t => t.image!)
          .concat(result.success ? [{
            expert_name: expertName,
            image_url: result.image_url!,
            prompt: prompt.trim(),
            prompt_used: prompt.trim(),
            id: result.image_id,
            aspect_ratio: aspectRatio,
            style_type: styleType,
            created_at: new Date().toISOString()
          }] : []);
        onImagesUpdated(allImages);
      }
    } catch (error: any) {
      console.error('生成图片失败:', error);
      setChatHistory(prev => {
        const newHistory = prev.filter(t => !t.isLoading);
        const errorTurn: ImageChatTurn = {
          turn_id: `error-${Date.now()}`,
          type: 'assistant',
          timestamp: new Date().toISOString(),
          error: error?.message || '网络错误，请重试'
        };
        return [...newHistory, errorTurn];
      });
    } finally {
      setIsGenerating(false);
    }
  };

  // ==================== 保存对话历史 ====================
  const saveChatHistory = async () => {
    try {
      await api.saveImageChatHistory(sessionId, expertName, chatHistory);
    } catch (error) {
      console.error('保存对话历史失败:', error);
    }
  };

  // ==================== 删除消息 ====================
  const handleDeleteTurn = async (turnId: string) => {
    const turn = chatHistory.find(t => t.turn_id === turnId);
    if (!turn) return;

    // 如果是AI响应且有图片，需要调用后端删除
    if (turn.type === 'assistant' && turn.image?.id) {
      try {
        await api.deleteImage(sessionId, expertName, turn.image.id);
      } catch (error) {
        console.error('删除图片失败:', error);
      }
    }

    // 从历史中移除
    setChatHistory(prev => prev.filter(t => t.turn_id !== turnId));
    
    // 保存更新后的历史
    await saveChatHistory();

    // 通知父组件
    if (onImagesUpdated) {
      const remainingImages = chatHistory
        .filter(t => t.turn_id !== turnId && t.type === 'assistant' && t.image)
        .map(t => t.image!);
      onImagesUpdated(remainingImages);
    }
  };

  // ==================== 参考图上传 ====================
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      alert('请选择图片文件');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      alert('图片大小不能超过 10MB');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      setReferenceImage(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  // ==================== 图片查看器 ====================
  const openImageViewer = (image: ExpertGeneratedImage) => {
    setViewingImage(image);
    setZoomLevel(1);
  };

  const closeImageViewer = () => {
    setViewingImage(null);
    setZoomLevel(1);
  };

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoomLevel(prev => Math.max(0.5, Math.min(3, prev + delta)));
  }, []);

  const handleDownloadImage = () => {
    if (!viewingImage) return;
    const link = document.createElement('a');
    link.href = viewingImage.image_url;
    link.download = `${expertName}-concept-${Date.now()}.png`;
    link.click();
  };

  // ==================== 快捷键 ====================
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ==================== 渲染 ====================
  if (!isOpen) return null;

  return (
    <>
      {/* 主对话窗口 */}
      <div className="fixed inset-0 z-[90] bg-black/90 backdrop-blur-sm flex flex-col">
        {/* 顶栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-[#0a0a0a]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <ImageIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">与 {expertName} 的图片对话</h2>
              <p className="text-sm text-white/50">{chatHistory.filter(t => t.type === 'assistant' && t.image).length} 张图片</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-white/70" />
          </button>
        </div>

        {/* 对话历史区域 */}
        <div
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto px-6 py-4 space-y-4"
        >
          {isLoadingHistory ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
            </div>
          ) : chatHistory.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-white/50">
              <ImageIcon className="w-16 h-16 mb-4 opacity-30" />
              <p>开始对话，描述您想要的图片</p>
            </div>
          ) : (
            chatHistory.map((turn) => (
              <ChatMessage
                key={turn.turn_id}
                turn={turn}
                onDelete={() => handleDeleteTurn(turn.turn_id)}
                onViewImage={() => turn.image && openImageViewer(turn.image)}
              />
            ))
          )}
        </div>

        {/* 智能推荐提示词 */}
        {suggestedPrompts.length > 0 && !isGenerating && (
          <div className="px-6 py-2 border-t border-white/5">
            <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-hide">
              <Sparkles className="w-4 h-4 text-amber-400 flex-shrink-0" />
              {suggestedPrompts.slice(0, 4).map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => setPrompt(suggestion.prompt)}
                  className="flex-shrink-0 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-sm text-white/70 hover:text-white transition-colors"
                >
                  {suggestion.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 输入区域 */}
        <div className="px-6 py-4 border-t border-white/10 bg-[#0a0a0a]">
          {/* 参数选择行 */}
          <div className="flex items-center gap-3 mb-3">
            {/* 上传参考图 */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
                referenceImage
                  ? 'bg-blue-500/20 border-blue-500/50 text-blue-400'
                  : 'bg-white/5 border-white/10 text-white/70 hover:bg-white/10'
              }`}
            >
              <Upload className="w-4 h-4" />
              <span className="text-sm">{referenceImage ? '已上传' : '参考图'}</span>
            </button>

            {/* 参考图预览 */}
            {referenceImage && (
              <div className="relative w-10 h-10 rounded-lg overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={referenceImage} alt="参考图" className="w-full h-full object-cover" />
                <button
                  onClick={() => {
                    setReferenceImage(null);
                    setEditMode(false);
                    setMaskData(null);
                  }}
                  className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center"
                >
                  <X className="w-3 h-3 text-white" />
                </button>
              </div>
            )}

            {/* 🔥 v7.62: 模式切换按钮（生成 vs 编辑） */}
            {referenceImage && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setEditMode(false);
                    setMaskData(null);
                  }}
                  className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                    !editMode
                      ? 'bg-blue-500/30 border border-blue-500/50 text-blue-300'
                      : 'bg-white/5 border border-white/10 text-white/50 hover:bg-white/10'
                  }`}
                >
                  🎨 生成新图
                </button>
                <button
                  onClick={() => setEditMode(true)}
                  className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                    editMode
                      ? 'bg-amber-500/30 border border-amber-500/50 text-amber-300'
                      : 'bg-white/5 border border-white/10 text-white/50 hover:bg-white/10'
                  }`}
                >
                  ✂️ 编辑现有图
                </button>
              </div>
            )}

            {/* 🔥 v7.61: Vision 分析开关（仅在生成模式 + 有参考图时显示） */}
            {referenceImage && !editMode && (
              <div className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10 rounded-lg">
                <input
                  type="checkbox"
                  checked={useVisionAnalysis}
                  onChange={(e) => setUseVisionAnalysis(e.target.checked)}
                  className="w-4 h-4 rounded"
                />
                <span className="text-sm text-white/70">Vision分析</span>
              </div>
            )}

            {/* 比例选择 */}
            <div className="relative">
              <button
                onClick={() => {
                  setShowAspectDropdown(!showAspectDropdown);
                  setShowStyleDropdown(false);
                }}
                className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white/70 hover:bg-white/10 transition-colors"
              >
                <span>{ASPECT_RATIO_OPTIONS.find(o => o.value === aspectRatio)?.icon}</span>
                <span>{aspectRatio}</span>
                <ChevronDown className="w-4 h-4" />
              </button>
              {showAspectDropdown && (
                <div className="absolute bottom-full mb-2 left-0 bg-[#1a1a1a] border border-white/10 rounded-lg shadow-xl overflow-hidden z-10">
                  {ASPECT_RATIO_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setAspectRatio(option.value);
                        setShowAspectDropdown(false);
                      }}
                      className={`w-full px-4 py-2 text-left text-sm flex items-center gap-3 hover:bg-white/10 ${
                        aspectRatio === option.value ? 'text-blue-400' : 'text-white/70'
                      }`}
                    >
                      <span>{option.icon}</span>
                      <span>{option.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 风格选择 */}
            <div className="relative">
              <button
                onClick={() => {
                  setShowStyleDropdown(!showStyleDropdown);
                  setShowAspectDropdown(false);
                }}
                className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white/70 hover:bg-white/10 transition-colors"
              >
                <span>{STYLE_TYPE_OPTIONS.find(o => o.value === styleType)?.label}</span>
                <ChevronDown className="w-4 h-4" />
              </button>
              {showStyleDropdown && (
                <div className="absolute bottom-full mb-2 left-0 bg-[#1a1a1a] border border-white/10 rounded-lg shadow-xl overflow-hidden z-10">
                  {STYLE_TYPE_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setStyleType(option.value);
                        setShowStyleDropdown(false);
                      }}
                      className={`w-full px-4 py-2 text-left text-sm hover:bg-white/10 ${
                        styleType === option.value ? 'text-blue-400' : 'text-white/70'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 🔥 v7.62: Mask 编辑器（仅在编辑模式 + 有参考图时显示） */}
          {editMode && referenceImage && (
            <div className="mb-4">
              <MaskEditor
                imageUrl={referenceImage}
                onMaskChange={(maskBase64) => setMaskData(maskBase64)}
              />
            </div>
          )}

          {/* 输入框 */}
          <div className="flex items-end gap-3">
            <div className="flex-1 relative">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="描述您想要的图片效果..."
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 resize-none focus:outline-none focus:border-blue-500/50 transition-colors"
                rows={2}
                disabled={isGenerating}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!prompt.trim() || isGenerating}
              className={`p-3 rounded-xl transition-all ${
                prompt.trim() && !isGenerating
                  ? 'bg-blue-500 hover:bg-blue-600 text-white'
                  : 'bg-white/10 text-white/30 cursor-not-allowed'
              }`}
            >
              {isGenerating ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : (
                <Send className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 图片查看器（纯查看模式） */}
      {viewingImage && (
        <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-sm flex items-center justify-center">
          {/* 顶部操作栏 */}
          <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-4 py-3 bg-gradient-to-b from-black/80 to-transparent">
            <div className="text-sm text-white/90 font-medium">
              {viewingImage.expert_name} - 概念图
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleDownloadImage}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                title="下载图片"
              >
                <Download className="w-5 h-5 text-white/70 hover:text-white" />
              </button>
              <button
                onClick={closeImageViewer}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                title="关闭"
              >
                <X className="w-5 h-5 text-white/70 hover:text-white" />
              </button>
            </div>
          </div>

          {/* 图像区域 */}
          <div
            ref={imageContainerRef}
            className="max-w-[90vw] max-h-[80vh] overflow-hidden cursor-zoom-in"
            onWheel={handleWheel}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={viewingImage.image_url}
              alt={`${viewingImage.expert_name} 概念图`}
              className="max-w-full max-h-[80vh] object-contain transition-transform duration-200"
              style={{ transform: `scale(${zoomLevel})` }}
            />
          </div>

          {/* 底部缩放提示 */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 px-4 py-2 bg-black/60 rounded-full text-sm text-white/70">
            滚轮缩放 · 当前 {Math.round(zoomLevel * 100)}%
          </div>
        </div>
      )}
    </>
  );
}

// ==================== 子组件：聊天消息 ====================
interface ChatMessageProps {
  turn: ImageChatTurn;
  onDelete: () => void;
  onViewImage: () => void;
}

function ChatMessage({ turn, onDelete, onViewImage }: ChatMessageProps) {
  if (turn.type === 'user') {
    // 用户消息 - 右对齐
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%] bg-blue-600/20 border border-blue-600/30 rounded-2xl rounded-tr-sm px-4 py-3">
          <p className="text-sm text-white whitespace-pre-wrap">{turn.prompt}</p>
          {turn.aspect_ratio && (
            <div className="mt-2 flex items-center gap-2 text-xs text-blue-400/70">
              <span>比例: {turn.aspect_ratio}</span>
              {turn.style_type && <span>· 风格: {turn.style_type}</span>}
            </div>
          )}
          {turn.reference_image_url && (
            <div className="mt-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={turn.reference_image_url}
                alt="参考图"
                className="w-16 h-16 rounded-lg object-cover opacity-70"
              />
            </div>
          )}
        </div>
      </div>
    );
  }

  // AI 响应
  if (turn.isLoading) {
    return (
      <div className="flex justify-start">
        <div className="bg-white/5 border border-white/10 rounded-2xl rounded-tl-sm px-4 py-3">
          <div className="flex items-center gap-2">
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
            <span className="text-sm text-white/70">正在生成图片...</span>
          </div>
        </div>
      </div>
    );
  }

  if (turn.error) {
    return (
      <div className="flex justify-start">
        <div className="bg-red-500/10 border border-red-500/30 rounded-2xl rounded-tl-sm px-4 py-3">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle className="w-5 h-5" />
            <span className="text-sm">{turn.error}</span>
          </div>
        </div>
      </div>
    );
  }

  if (turn.image) {
    return (
      <div className="flex justify-start">
        <div className="group relative max-w-[70%] bg-white/5 border border-white/10 rounded-2xl rounded-tl-sm overflow-hidden">
          {/* 图片区域 */}
          <div
            className="relative cursor-pointer"
            onClick={onViewImage}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={turn.image.image_url}
              alt="生成的图片"
              className="w-full max-w-md rounded-t-xl transition-transform duration-300 hover:scale-[1.02]"
            />
            {/* 悬停时显示查看图标 */}
            <div className="absolute inset-0 bg-black/0 hover:bg-black/30 flex items-center justify-center opacity-0 hover:opacity-100 transition-all">
              <Maximize2 className="w-8 h-8 text-white" />
            </div>
          </div>
          
          {/* 悬停时显示删除按钮 */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 p-2 bg-black/60 hover:bg-red-500/80 rounded-lg text-white/80 hover:text-white"
            title="删除这条记录"
          >
            <Trash2 className="w-4 h-4" />
          </button>

          {/* 提示词信息 */}
          <div className="px-4 py-3">
            <p className="text-xs text-white/50 line-clamp-2">
              {turn.image.prompt_used || turn.image.prompt}
            </p>
            {turn.image.aspect_ratio && (
              <div className="mt-1 text-xs text-white/30">
                {turn.image.aspect_ratio} · {turn.image.style_type || 'conceptual'}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
