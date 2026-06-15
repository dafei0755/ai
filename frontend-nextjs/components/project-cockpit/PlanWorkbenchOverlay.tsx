'use client';
/**
 * PlanWorkbenchOverlay — 平面推演工作台 · 半透明覆盖层悬浮窗
 *
 * 设计原则（项目宪法 v1.2）：
 *   项目底盘是主场，泡泡逻辑是思考，平面穿透窗是几何影子，
 *   悬浮覆盖层是硫酸纸 — 不融合，只穿透；不切换，只显隐。
 *
 * 行为：
 *   - 半透明遮罩覆盖整个底盘（背景 ~30% 可见，作为视觉锚点）
 *   - 浮窗居中悬浮 75% × 80%，主体内容区不透明，工具/图纸完全清晰
 *   - Esc / 右上角 X / 点击外部空白 关闭
 *   - 关闭后底盘焦点完全保留（不重置）
 *   - 浮窗打开时屏蔽底盘交互 + 阻断鼠标滚轮穿透
 *   - 使用 React Portal 渲染至 document.body，规避父级 stacking-context 问题
 */
import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { PlanSandboxPanel } from '@/components/PlanSandboxPanel';
import type { ProjectOverview } from './mock/mockData';

type PlanSandboxSpace = '大堂' | '餐厅' | '客房' | '公区' | '连廊' | '后勤';
const PLAN_SANDBOX_SPACES: PlanSandboxSpace[] = ['大堂', '餐厅', '客房', '公区', '连廊', '后勤'];

/** zoneId → PlanSandboxPanel 接受的 activeSpace */
const ZONE_TO_PLAN_SPACE: Record<string, PlanSandboxSpace> = {
  entry:   '公区',
  lobby:   '大堂',
  dining:  '餐厅',
  zone_a:  '客房',
  service: '后勤',
};

export interface PlanOverlayContext {
  bubbleName?: string;
  zoneLabel?: string;
  zoneId?: string;
  roomLabel?: string;
  bindingState: 'unbound' | 'candidate' | 'bound';
}

interface PlanWorkbenchOverlayProps {
  open: boolean;
  context: PlanOverlayContext;
  onClose: () => void;
  /** 装载 PlanSandboxPanel 所需的 session 上下文 */
  sessionId?: string;
  projectLabel?: string;
  projectOverview?: ProjectOverview;
}

export default function PlanWorkbenchOverlay({
  open, context, onClose,
  sessionId, projectLabel, projectOverview,
}: PlanWorkbenchOverlayProps) {
  const [mounted, setMounted] = useState(false);
  // 当前 zone 对应的 PlanSandboxSpace（每个 tile 各自独立）
  const initialSpace: PlanSandboxSpace = (context.zoneId && ZONE_TO_PLAN_SPACE[context.zoneId]) || '大堂';
  const [activeSpace, setActiveSpace] = useState<PlanSandboxSpace>(initialSpace);

  useEffect(() => { setMounted(true); }, []);

  // 浮窗每次打开时，按当前 tile 的 zoneId 重置 activeSpace
  useEffect(() => {
    if (!open) return;
    const target = (context.zoneId && ZONE_TO_PLAN_SPACE[context.zoneId]) || '大堂';
    setActiveSpace(target);
  }, [open, context.zoneId]);

  // Esc 关闭（capture phase，确保最高优先级）
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handler, true);
    return () => window.removeEventListener('keydown', handler, true);
  }, [open, onClose]);

  // 锁定背景滚动
  useEffect(() => {
    if (!open) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prevOverflow; };
  }, [open]);

  if (!open || !mounted) return null;

  // 面包屑路径
  const breadcrumb: string[] = ['项目底盘'];
  if (context.bubbleName) breadcrumb.push(context.bubbleName);
  if (context.zoneLabel && context.zoneLabel !== context.bubbleName) breadcrumb.push(context.zoneLabel);
  if (context.roomLabel) breadcrumb.push(context.roomLabel);
  breadcrumb.push('平面推演');

  // 阻断滚轮 / 触摸 穿透到底盘
  const blockScroll = (e: React.WheelEvent | React.TouchEvent) => {
    e.stopPropagation();
  };

  const overlayContent = (
    <div
      role="dialog"
      aria-modal="true"
      onPointerDown={(e) => {
        e.stopPropagation();
        if (e.target === e.currentTarget) onClose();
      }}
      onClick={(e) => e.stopPropagation()}
      onWheel={blockScroll}
      onTouchMove={blockScroll}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        background: 'rgba(8, 12, 18, 0.55)',
        backdropFilter: 'blur(2px)',
        WebkitBackdropFilter: 'blur(2px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        animation: 'planOverlayFadeIn 180ms ease-out',
      }}
    >
      <style>{`
        @keyframes planOverlayFadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes planOverlayPanelIn {
          from { opacity: 0; transform: scale(0.97); }
          to { opacity: 1; transform: scale(1); }
        }
      `}</style>

      <div
        onPointerDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
        onWheel={(e) => e.stopPropagation()}
        style={{
          position: 'relative',
          width: '78vw',
          height: '82vh',
          maxWidth: '1600px',
          maxHeight: '1000px',
          background: '#ffffff',
          boxShadow: '0 24px 80px rgba(0,0,0,0.45), 0 4px 16px rgba(0,0,0,0.25)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'planOverlayPanelIn 220ms cubic-bezier(0.2, 0.8, 0.2, 1)',
        }}
      >
        {/* 浮窗头部 */}
        <header
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px 18px',
            borderBottom: '1px solid #e2e8f0',
            background: '#f8fafc',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
            <div style={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: '0.14em',
              color: '#0ea5e9',
              textTransform: 'uppercase',
            }}>
              平面推演 · 悬浮工作台
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 13,
              color: '#475569',
              flexWrap: 'wrap',
            }}>
              {breadcrumb.map((seg, i) => (
                <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{
                    color: i === breadcrumb.length - 1 ? '#0f172a' : '#64748b',
                    fontWeight: i === breadcrumb.length - 1 ? 600 : 400,
                  }}>
                    {seg}
                  </span>
                  {i < breadcrumb.length - 1 && (
                    <span style={{ color: '#cbd5e1' }}>›</span>
                  )}
                </span>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
            <span
              style={{
                fontSize: 11,
                padding: '3px 9px',
                background:
                  context.bindingState === 'bound' ? '#dcfce7'
                    : context.bindingState === 'candidate' ? '#fef3c7'
                      : '#f1f5f9',
                color:
                  context.bindingState === 'bound' ? '#166534'
                    : context.bindingState === 'candidate' ? '#92400e'
                      : '#64748b',
                fontWeight: 600,
                letterSpacing: '0.04em',
              }}
            >
              {context.bindingState === 'bound' ? '已绑定平面'
                : context.bindingState === 'candidate' ? '候选绑定'
                  : '未绑定平面'}
            </span>
            <button
              type="button"
              onPointerDown={(e) => {
                e.stopPropagation();
                e.preventDefault();
                onClose();
              }}
              onClick={(e) => {
                e.stopPropagation();
                e.preventDefault();
              }}
              aria-label="关闭悬浮工作台"
              style={{
                width: 36,
                height: 36,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#ffffff',
                border: '1px solid #cbd5e1',
                color: '#475569',
                cursor: 'pointer',
                fontSize: 18,
                lineHeight: 1,
                fontWeight: 300,
                transition: 'all 120ms',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#fee2e2';
                e.currentTarget.style.borderColor = '#fca5a5';
                e.currentTarget.style.color = '#b91c1c';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#ffffff';
                e.currentTarget.style.borderColor = '#cbd5e1';
                e.currentTarget.style.color = '#475569';
              }}
            >
              ×
            </button>
          </div>
        </header>

        {/* 浮窗主体 — 平面推演工作区 */}
        <main
          style={{
            flex: 1,
            background: '#0d1117',
            position: 'relative',
            overflow: 'hidden',
            minHeight: 0,
          }}
          onWheel={(e) => e.stopPropagation()}
        >
          {sessionId ? (
            <PlanSandboxPanel
              sessionId={sessionId}
              projectLabel={projectLabel}
              projectOverview={projectOverview}
              activeSpace={activeSpace}
              spaceOptions={PLAN_SANDBOX_SPACES}
              onActiveSpaceChange={setActiveSpace}
              className="w-full h-full"
            />
          ) : (
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <div style={{ textAlign: 'center', maxWidth: 540, padding: 40 }}>
                <div
                  style={{
                    width: 64, height: 64, margin: '0 auto 20px',
                    border: '1.5px dashed rgba(255,255,255,0.30)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 26, color: 'rgba(255,255,255,0.55)',
                  }}
                >
                  ◧
                </div>
                <div style={{
                  fontSize: 16, fontWeight: 600,
                  color: 'rgba(255,255,255,0.92)', marginBottom: 10,
                }}>
                  平面推演工作台
                </div>
                <div style={{
                  fontSize: 12, lineHeight: 1.7,
                  color: 'rgba(255,255,255,0.50)', marginBottom: 18,
                }}>
                  当前作用域：<span style={{ color: 'rgba(255,255,255,0.78)' }}>
                    {context.zoneLabel ?? context.bubbleName ?? '项目总图'}
                  </span>
                </div>
                <div style={{
                  fontSize: 11, lineHeight: 1.8,
                  color: 'rgba(255,255,255,0.36)',
                  padding: '14px 18px',
                  border: '1px solid rgba(255,255,255,0.10)',
                  background: 'rgba(255,255,255,0.02)',
                  textAlign: 'left',
                }}>
                  缺少 sessionId — 无法装载真实平面推演组件。<br />
                  此处将装载 PlanSandboxPanel 完整能力：<br />
                  · 图纸基线 · IR 五门校验 · 识别质量<br />
                  · 门窗洞 / 墙线对象 / 结构 / 闭合空间<br />
                  · 比例尺标 / 重选识别区 / 注入高参
                </div>
              </div>
            </div>
          )}

          {/* 角落 watermark */}
          <div
            style={{
              position: 'absolute',
              bottom: 12,
              right: 16,
              fontSize: 9,
              letterSpacing: '0.16em',
              color: 'rgba(255,255,255,0.25)',
              fontFamily: "'Courier New', monospace",
              pointerEvents: 'none',
              background: 'rgba(13,17,23,0.65)',
              padding: '3px 8px',
            }}
          >
            ESC 关闭 · 回到项目底盘
          </div>
        </main>
      </div>
    </div>
  );

  // 用 React Portal 渲染到 body —— 规避父级 stacking-context / transform 引起的事件问题
  return createPortal(overlayContent, document.body);
}
