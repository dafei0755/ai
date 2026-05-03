'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import type { AdvisorFocus } from './mock/mockData';

interface AdvisorOutput {
  focus: string;
  stage: string;
  judgment: string;
  suggestion: string;
  cannotDo?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'advisor';
  text: string;
  isThinking?: boolean;
}

interface AdvisorPanelProps {
  advisorFocus: AdvisorFocus;
  switchNotice?: string;
  output: AdvisorOutput;
  inputPlaceholder: string;
  prefillMessage?: string;
  onSend: (text: string) => void;
}

// ── Mock 响应逻辑 ──────────────────────────────────────────────────────────
function getMockResponse(input: string): string {
  const text = input.toLowerCase();

  if (text.includes('平面图') || text.includes('上传')) {
    return `有了平面图之后，我可以做三件事：\n\n1. 识别空间结构和动线关系\n2. 对照山地民宿标准判断各空间面积是否合理\n3. 给出平面推演的第一版方向建议\n\n上传前先确认：是现场测绘图还是设计草稿？`;
  }

  if (text.includes('方向') || text.includes('概念') || text.includes('定位') || text.includes('草案') || text.includes('保存')) {
    return `好，当前方向已整理为草案：\n\n**项目方向**：HAY 气质 × 七里坪山地 × 轻度假精品民宿\n**设计路线**：「山间轻居」— 克制 / 功能主义 / 看山留白\n**当前状态**：草案（待补：面积 / 房型 / 平面）\n\n你认可这个方向吗？确认后可以进入空间分类。`;
  }

  if (text.includes('缺口') || text.includes('补充') || text.includes('面积') || text.includes('房间')) {
    return `当前主要缺口按优先级排：\n\n1. **总建筑面积和各空间面积分布**（影响平面推演起点）\n2. **客房数量和房型组合**（影响运营密度判断）\n3. **现场平面图或测绘图**（影响空间策略准确性）\n\n哪个你现在方便补？`;
  }

  if (text.includes('大堂') || text.includes('客房') || text.includes('餐厅') || text.includes('空间')) {
    return `七里坪项目的空间优先级建议：\n\n**首优先**：公共大堂（品牌第一印象）+ 观景露台（核心卖点）\n**次优先**：标准客房（运营主体）\n**按需规划**：餐饮轻服务区、后勤区\n\n有平面图后，我可以给出更精准的面积分配建议。`;
  }

  if (text.includes('主矛盾') || text.includes('矛盾')) {
    return `当前主矛盾是**品牌气质 vs 山地在地性**。\n\nHAY 的克制美学需要和峨眉山的自然粗粝共存，而不是简单叠加。\n\n我的判断是：用材料语言做连接——本地自然材料（石、木）作为肌底，HAY 风格的家具和灯具作为气质载体。这样两者各自成立，不互相消解。\n\n你觉得这个方向可以推进吗？`;
  }

  return `听到了。\n\n当前底盘已覆盖：品牌气质 / 地点约束 / 目标人群。\n主要缺口：面积分布、房间数量、平面结构。\n\n补上这三点，我可以给出更准确的推演和空间策略建议。你想先从哪个方向入手？`;
}

export function AdvisorPanel({
  switchNotice,
  output,
  inputPlaceholder,
  prefillMessage,
  onSend,
}: AdvisorPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [showNotice, setShowNotice] = useState(!!switchNotice);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prefillMessage) {
      setInputValue(prefillMessage);
    }
  }, [prefillMessage]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text) return;

    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', text };
    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsThinking(true);
    onSend(text);

    setTimeout(() => {
      setIsThinking(false);
      setMessages(prev => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: 'advisor', text: getMockResponse(text) },
      ]);
    }, 1500);
  };

  const hasChatHistory = messages.length > 0;

  return (
    <div className="flex flex-col h-full bg-[#161616] text-white">
      {/* 标题栏 */}
      <div className="flex items-center gap-3 border-b border-white/8 px-4 py-3.5 shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#2e67ff] text-white shrink-0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <span className="text-sm font-semibold text-white">方案高参</span>
      </div>

      {/* 切换通知 */}
      {showNotice && switchNotice && (
        <div className="mx-3 mt-2 px-3 py-1.5 rounded-md bg-white/5 border border-white/10 flex items-center justify-between shrink-0">
          <span className="text-xs text-white/60">{switchNotice}</span>
          <button onClick={() => setShowNotice(false)} className="text-white/40 hover:text-white/70 ml-2 text-sm leading-none">×</button>
        </div>
      )}

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        {!hasChatHistory && (
          <>
            <section>
              <p className="text-[10px] font-semibold text-white/38 uppercase tracking-widest mb-1.5">我正在看</p>
              <p className="text-sm text-white leading-relaxed">{output.focus}</p>
            </section>
            <section>
              <p className="text-[10px] font-semibold text-white/38 uppercase tracking-widest mb-1.5">当前状态</p>
              <p className="text-sm text-white/90 font-medium leading-relaxed">{output.stage}</p>
              {output.judgment && (
                <p className="mt-1.5 text-sm text-white/60 leading-relaxed">{output.judgment}</p>
              )}
            </section>
            <section>
              <p className="text-[10px] font-semibold text-white/38 uppercase tracking-widest mb-1.5">我建议</p>
              <p className="text-sm text-white/90 leading-relaxed">{output.suggestion}</p>
            </section>
            {output.cannotDo && (
              <section>
                <p className="text-[10px] font-semibold text-white/38 uppercase tracking-widest mb-1.5">现在不能做</p>
                <p className="text-sm text-white/50 leading-relaxed">{output.cannotDo}</p>
              </section>
            )}
            <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-2 mt-2">
              <span className="text-[10px] text-white/30 leading-relaxed">随时开始聊 — 分享你的想法、灵感或设计需求</span>
            </div>
          </>
        )}

        {hasChatHistory && (
          <>
            <div className="rounded-lg bg-white/5 px-3 py-2 text-xs text-white/40 border border-white/8">
              <span className="font-medium text-white/60">当前状态：</span>{output.stage} · {output.suggestion.slice(0, 20)}...
            </div>

            {messages.map(msg => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
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

      {/* 输入框 */}
      <div className="px-3 pb-3 pt-2 border-t border-white/8 shrink-0">
        <div className="flex items-end gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 focus-within:border-white/20 transition-colors">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={inputPlaceholder}
            rows={2}
            className="flex-1 bg-transparent text-sm text-white placeholder:text-white/30 resize-none outline-none leading-relaxed"
            onKeyDown={(e) => {
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
