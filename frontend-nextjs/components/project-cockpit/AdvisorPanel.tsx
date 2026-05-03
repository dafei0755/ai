'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import type { AdvisorViewModel, ActionChip } from '@/types/advisor';

interface AdvisorPanelProps {
  viewModel: AdvisorViewModel;
  prefillMessage?: string;
  onChipAction: (chip: ActionChip) => void;
  onAsk: (text: string) => void;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'advisor';
  text: string;
}

const EVIDENCE_CONFIG = {
  none:          { dot: 'bg-gray-500',   label: '无依据' },
  internal_hint: { dot: 'bg-yellow-400', label: '内部推断' },
  verified:      { dot: 'bg-green-400',  label: '已验证' },
} as const;

const MODULE_LABELS: Record<string, string> = {
  project_base:   '项目底盘',
  floor_plan:     '平面推演',
  scheme_canvas:  '方案画布',
  resource_radar: '资源雷达',
  silicon_avatar: '硅基分身',
  knowledge_hub:  '知识中枢',
};

const OBJECT_STATE_LABELS: Record<string, string> = {
  draft:               '草案',
  pending_confirmation: '待确认',
  frozen:              '已冻结',
  stale:               '已过期',
  forked:              '已分叉',
  archived:            '已归档',
};

export function AdvisorPanel({
  viewModel,
  prefillMessage,
  onChipAction,
  onAsk,
}: AdvisorPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prefillMessage) setInputValue(prefillMessage);
  }, [prefillMessage]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text || isThinking) return;
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', text }]);
    setInputValue('');
    setIsThinking(true);
    onAsk(text);
    setTimeout(() => {
      setIsThinking(false);
      setMessages(prev => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: 'advisor', text: viewModel.judgment.content },
      ]);
    }, 1200);
  };

  const handleChipClick = (chip: ActionChip) => {
    if (chip.type === 'ask') {
      setInputValue(chip.payload.question);
    } else {
      onChipAction(chip);
    }
  };

  const hasChatHistory = messages.length > 0;
  const evidenceConfig = EVIDENCE_CONFIG[viewModel.evidenceStatus];
  const renderableChips = viewModel.actionChips.filter(
    c => c.type === 'ask' || c.type === 'navigate' || c.type === 'fill'
  );
  const primaryChips = renderableChips.filter(c => c.isPrimary);
  const secondaryChips = renderableChips.filter(c => !c.isPrimary).slice(0, 2);

  return (
    <div className="flex flex-col h-full bg-[#161616] text-white">

      {/* ① 标题栏 + 场景绑定 */}
      <div className="flex items-center gap-3 border-b border-white/8 px-4 py-3.5 shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#2e67ff] text-white shrink-0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <span className="text-sm font-semibold text-white">方案高参</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="text-[10px] text-white/40">
              {MODULE_LABELS[viewModel.sceneContext.module] ?? viewModel.sceneContext.module}
              {viewModel.objectState && ` · ${OBJECT_STATE_LABELS[viewModel.objectState] ?? viewModel.objectState}`}
            </span>
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${evidenceConfig.dot}`} />
            <span className="text-[10px] text-white/40">{evidenceConfig.label}</span>
          </div>
        </div>
      </div>

      {/* ② 判断区 */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {!hasChatHistory ? (
          <>
            <section>
              <p className="text-[10px] font-semibold text-white/38 uppercase tracking-widest mb-1.5">
                我正在看
              </p>
              <p className="text-sm text-white/80 leading-relaxed">
                {viewModel.boundObjectId ?? viewModel.sceneContext.objectId ?? viewModel.sceneContext.sessionId}
              </p>
            </section>
            <section>
              <p className="text-[10px] font-semibold text-white/38 uppercase tracking-widest mb-1.5">
                判断
              </p>
              <p className="text-sm text-white/90 leading-relaxed">{viewModel.judgment.content}</p>
              {viewModel.judgment.confidence === 'low' && (
                <p className="mt-1 text-[10px] text-yellow-400/70">
                  置信度低，建议补充信息后重新评估
                </p>
              )}
            </section>
          </>
        ) : (
          <>
            <div className="rounded-lg bg-white/5 px-3 py-2 text-xs text-white/40 border border-white/8 shrink-0">
              <span className="font-medium text-white/60">
                {OBJECT_STATE_LABELS[viewModel.objectState ?? 'draft'] ?? '草案'}：
              </span>
              {viewModel.judgment.content.slice(0, 40)}...
            </div>
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'advisor' && (
                  <div className="h-6 w-6 rounded-full bg-[#2e67ff] flex items-center justify-center shrink-0 mr-2 mt-0.5">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                    </svg>
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-line ${
                    msg.role === 'user'
                      ? 'bg-[#2e67ff] text-white rounded-tr-sm'
                      : 'bg-white/8 text-white/90 rounded-tl-sm'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {isThinking && (
              <div className="flex justify-start">
                <div className="h-6 w-6 rounded-full bg-[#2e67ff] flex items-center justify-center shrink-0 mr-2 mt-0.5">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                  </svg>
                </div>
                <div className="bg-white/8 rounded-2xl rounded-tl-sm px-3.5 py-2.5 flex items-center gap-1.5">
                  <Loader2 className="w-3.5 h-3.5 text-white/50 animate-spin" />
                  <span className="text-xs text-white/40">思考中...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* ③ ActionChip 区 */}
      <div className="px-3 pb-2 shrink-0 space-y-1.5">
        {primaryChips.map((chip, i) => (
          <button
            key={i}
            onClick={() => handleChipClick(chip)}
            className="w-full text-left rounded-lg bg-[#2e67ff] px-3 py-2 text-sm font-medium text-white hover:bg-[#2558e0] transition-colors"
          >
            {chip.label}
          </button>
        ))}
        {secondaryChips.length > 0 && (
          <div className="flex gap-1.5">
            {secondaryChips.map((chip, i) => (
              <button
                key={i}
                onClick={() => handleChipClick(chip)}
                className="flex-1 rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white/70 hover:border-white/30 hover:text-white transition-colors"
              >
                {chip.label}
              </button>
            ))}
          </div>
        )}
        {viewModel.judgment.cannotDo?.map((item, i) => (
          <p key={i} className="text-[10px] text-white/30 px-1">
            {item.reason}
          </p>
        ))}
      </div>

      {/* ④ 已激活能力（Phase A1 占位，纯展示） */}
      <div className="px-3 pb-2 shrink-0">
        <div className="rounded-lg bg-white/3 border border-white/8 px-3 py-2">
          <p className="text-[10px] font-semibold text-white/30 uppercase tracking-widest mb-1.5">
            已激活能力
          </p>
          <div className="flex gap-2 flex-wrap">
            {viewModel.activatedCapabilities.map((cap, i) => (
              <span
                key={i}
                className={`text-[10px] px-2 py-0.5 rounded-full border ${
                  cap.status === 'placeholder'
                    ? 'border-white/10 text-white/25'
                    : 'border-blue-500/40 text-blue-400/70'
                }`}
              >
                {cap.name}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ⑤ 输入框 */}
      <div className="px-3 pb-3 pt-1 border-t border-white/8 shrink-0">
        <div className="flex items-end gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 focus-within:border-white/20 transition-colors">
          <textarea
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            placeholder="问我任何关于这个项目的问题..."
            rows={2}
            className="flex-1 bg-transparent text-sm text-white placeholder:text-white/30 resize-none outline-none leading-relaxed"
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isThinking}
            className="shrink-0 p-1.5 rounded-lg text-[#2e67ff] disabled:opacity-30 hover:bg-white/8 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

    </div>
  );
}
