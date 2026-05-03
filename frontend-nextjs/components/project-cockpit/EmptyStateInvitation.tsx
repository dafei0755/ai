'use client';

import { useState } from 'react';
import { MessageSquare, Upload, Image, LayoutTemplate, Loader2 } from 'lucide-react';

export type EntryType = 'chat' | 'floor_plan' | 'reference_image' | 'template';

interface EntryOption {
  type: EntryType;
  icon: React.ReactNode;
  label: string;
  description: string;
}

interface EmptyStateInvitationProps {
  onEntry: (type: EntryType) => void;
}

const ENTRY_OPTIONS: EntryOption[] = [
  {
    type: 'chat',
    icon: <MessageSquare className="w-5 h-5" />,
    label: '直接聊聊你的想法',
    description: '用你自己的方式描述，我来整理',
  },
  {
    type: 'floor_plan',
    icon: <Upload className="w-5 h-5" />,
    label: '上传一张平面图',
    description: '我来识别空间结构，你来确认',
  },
  {
    type: 'reference_image',
    icon: <Image className="w-5 h-5" />,
    label: '上传几张参考图',
    description: '先定气质方向，再深化',
  },
  {
    type: 'template',
    icon: <LayoutTemplate className="w-5 h-5" />,
    label: '从项目类型模板开始',
    description: '选一个类型，我提前备好框架',
  },
];

export function EmptyStateInvitation({ onEntry }: EmptyStateInvitationProps) {
  const [activating, setActivating] = useState<EntryType | null>(null);

  const handleClick = (type: EntryType) => {
    setActivating(type);
    setTimeout(() => {
      onEntry(type);
    }, 800);
  };

  return (
    <div className="flex flex-col items-center justify-center h-full px-8 py-16 text-center bg-[#f5f5f7]">
      <div className="mb-2 text-xl font-bold text-slate-800">
        欢迎来到项目底盘
      </div>
      <p className="mb-10 text-sm text-slate-500 max-w-sm leading-relaxed">
        我会陪你把这个项目从想法变成方案。
        <br />
        开始的方式有几种，选你最舒服的：
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-md">
        {ENTRY_OPTIONS.map((opt) => {
          const isActivating = activating === opt.type;
          return (
            <button
              key={opt.type}
              onClick={() => handleClick(opt.type)}
              disabled={activating !== null}
              className={`
                cockpit-card cockpit-card-interactive
                flex items-start gap-3 p-4 text-left
                ${isActivating ? 'cockpit-card-accent-files' : ''}
                ${activating !== null && !isActivating ? 'opacity-40' : ''}
              `}
            >
              <span className={`mt-0.5 shrink-0 transition-colors ${isActivating ? 'text-sky-600' : 'text-slate-400'}`}>
                {isActivating
                  ? <Loader2 className="w-5 h-5 animate-spin" />
                  : opt.icon}
              </span>
              <span className="flex flex-col gap-0.5">
                <span className="text-sm font-semibold text-slate-900">{opt.label}</span>
                <span className="text-xs text-slate-500">{opt.description}</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
