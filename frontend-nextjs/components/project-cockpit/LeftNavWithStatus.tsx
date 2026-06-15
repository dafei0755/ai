'use client';

import type { CapabilityStatus } from './mock/mockData';

export type LeftNavKey = CapabilityStatus['key'] | 'geo' | 'silicon_avatar';

interface LeftNavWithStatusProps {
  capabilities: CapabilityStatus[];
  activeKey?: LeftNavKey;
  onCapabilityClick: (key: LeftNavKey) => void;
}

const AUXILIARY_ITEMS = [
  { key: 'geo', label: '地理工作台' },
  { key: 'silicon_avatar', label: '我的硅基分身' },
] as const;

export function LeftNavWithStatus({ capabilities, activeKey, onCapabilityClick }: LeftNavWithStatusProps) {
  return (
    <div className="flex flex-col items-start gap-3">
      {/* 三大能力胶囊 */}
      {capabilities.map((cap) => {
        const isActive = cap.key === activeKey;
        return (
          <div
            key={cap.key}
            className={`w-[32px] overflow-hidden rounded-[18px] border shadow-[0_14px_32px_rgba(15,23,42,0.22)] backdrop-blur-md transition-all duration-300 ${
              isActive
                ? 'border-sky-300/80 bg-[#1fa2df] text-white'
                : 'border-slate-300 bg-[rgba(204,209,216,0.96)] text-slate-800'
            }`}
          >
            <button
              onClick={() => onCapabilityClick(cap.key)}
              className="flex w-full min-h-[100px] items-center justify-center px-0 py-4 text-center"
              title={`${cap.label} · ${cap.statusLabel}`}
            >
              <div className="flex flex-col items-center leading-none text-[13px] font-semibold">
                {cap.label.split('').map((char, i) => (
                  <span key={i}>{char}</span>
                ))}
              </div>
            </button>
          </div>
        );
      })}

      {/* 辅助功能胶囊 */}
      {AUXILIARY_ITEMS.map((item) => {
        const isActive = item.key === activeKey;
        return (
        <div
          key={item.key}
          className={`w-[32px] overflow-hidden rounded-[18px] border shadow-[0_14px_32px_rgba(15,23,42,0.22)] backdrop-blur-md transition-all duration-300 ${
            isActive
              ? 'border-sky-300/80 bg-[#1fa2df] text-white'
              : 'border-slate-300 bg-[rgba(204,209,216,0.96)] text-slate-800'
          }`}
        >
          <button
            onClick={() => onCapabilityClick(item.key)}
            className="flex w-full min-h-[120px] items-center justify-center px-0 py-4 text-center"
            title={item.label}
          >
            <div className="flex flex-col items-center leading-none text-[13px] font-semibold">
              {item.label.split('').map((char, i) => (
                <span key={i}>{char}</span>
              ))}
            </div>
          </button>
        </div>
        );
      })}
    </div>
  );
}
