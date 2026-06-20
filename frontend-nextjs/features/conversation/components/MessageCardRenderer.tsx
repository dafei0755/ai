'use client';

import { ArrowRight, Check, RotateCcw, Sparkles, X } from 'lucide-react';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import CandidateCard, { type CandidateCardResponse } from '@/components/ConversationMode/CandidateCard';
import GuidanceCardWidget from '@/components/ConversationMode/GuidanceCard';
import type {
  ChatMessage,
  GuidanceCardData,
  GuidanceCardStructuredResponse,
  SchemeVersionCardData,
} from '@/features/conversation/types';

export interface MessageCardRendererProps {
  message: ChatMessage;
  onCardResponse?: (
    cardId: string,
    optionId?: string,
    freetext?: string,
    structuredResponse?: GuidanceCardStructuredResponse,
  ) => void | Promise<void>;
  onCandidateCardResponse?: (response: CandidateCardResponse) => void;
}

export function MessageCardRenderer({
  message,
  onCardResponse,
  onCandidateCardResponse,
}: MessageCardRendererProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end mb-5" data-testid="message-bubble">
        <div className="ui-type-body max-w-[min(78%,54rem)] px-5 py-3.5 rounded-[1.5rem] bg-[var(--card-bg)] text-[var(--foreground)]">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  const gc = message.guidance_card;
  const isCandidateCard = gc?.card_type === 'candidate';
  const isSchemeVersionCard = gc?.card_type === 'scheme_version_selection';

  return (
    <div className="mb-6" data-testid="message-bubble">
      <div className="ui-type-body text-[var(--foreground)] prose-conv">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => <h1 className="ui-type-title font-bold mt-5 mb-2 first:mt-0">{children}</h1>,
            h2: ({ children }) => <h2 className="ui-type-subtitle font-bold mt-5 mb-2 first:mt-0">{children}</h2>,
            h3: ({ children }) => <h3 className="ui-type-subtitle font-semibold mt-4 mb-2 first:mt-0">{children}</h3>,
            strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
            p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
            br: () => <br />,
            ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1.5">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1.5">{children}</ol>,
            li: ({ children }) => <li>{children}</li>,
            hr: () => <hr className="my-3 border-[var(--border-color)]" />,
            code: ({ children }) => <code className="px-1.5 py-0.5 rounded bg-[var(--border-color)] text-[0.85em] font-mono">{children}</code>,
          }}
        >
          {message.content}
        </ReactMarkdown>
      </div>

      {message.has_draft && message.draft_type && (
        <div className="ui-type-meta mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border-l-2 border-indigo-400 bg-indigo-500/10 text-indigo-400">
          <span>📎</span>
          <span>已记录 · <span className="font-medium">{message.draft_type}</span></span>
        </div>
      )}

      {gc && isCandidateCard && !message.card_responded && onCandidateCardResponse && gc.candidate_fields && (
        <div className="mt-4 max-w-[88%]">
          <CandidateCard
            card={{
              card_id: gc.card_id,
              card_type: (gc.card_type === 'candidate'
                ? (gc.gap_round ? 'gap' : 'echo')
                : 'echo') as 'echo' | 'gap',
              title: gc.title ?? gc.prompt_text,
              summary: gc.prompt_text,
              candidate_fields: gc.candidate_fields,
              card_status: gc.card_status ?? 'candidate',
              gap_round: gc.gap_round,
            }}
            onRespond={onCandidateCardResponse}
          />
        </div>
      )}

      {gc && isCandidateCard && message.card_responded && gc.candidate_fields && (
        <div className="mt-4 max-w-[88%]">
          <CandidateCard
            card={{
              card_id: gc.card_id,
              card_type: (gc.gap_round ? 'gap' : 'echo') as 'echo' | 'gap',
              title: gc.title ?? gc.prompt_text,
              summary: gc.prompt_text,
              candidate_fields: gc.candidate_fields,
              card_status: gc.card_status ?? 'confirmed',
              gap_round: gc.gap_round,
            }}
            initialResponded
            respondedSummary={message.card_selection_label}
            onRespond={() => {}}
          />
        </div>
      )}

      {gc && isSchemeVersionCard && !message.card_responded && onCardResponse && (
        <div className="mt-4 max-w-[min(96%,44rem)]">
          <SchemeVersionSelectionCard
            card={gc}
            onRespond={(optionId) => onCardResponse(gc.card_id, optionId)}
          />
        </div>
      )}

      {gc && isSchemeVersionCard && message.card_responded && onCardResponse && (
        <div className="mt-4 max-w-[min(96%,44rem)]">
          <SchemeVersionSelectionCard
            card={gc}
            initialResponded
            respondedSummary={message.card_selection_label}
            onRespond={(optionId) => onCardResponse(gc.card_id, optionId)}
          />
        </div>
      )}

      {gc && !isCandidateCard && !isSchemeVersionCard && !message.card_responded && onCardResponse && (
        <div className="mt-4 w-full">
          <GuidanceCardWidget
            card={gc}
            onRespond={(optionId, freetext, structuredResponse) =>
              onCardResponse(gc.card_id, optionId, freetext, structuredResponse)
            }
          />
        </div>
      )}

      {gc && !isCandidateCard && !isSchemeVersionCard && message.card_responded && (
        <div className="mt-4 w-full">
          <GuidanceCardWidget
            card={gc}
            initialResponded
            respondedSummary={message.card_selection_label}
            onRespond={() => {}}
          />
        </div>
      )}
    </div>
  );
}

function SchemeVersionSelectionCard({
  card,
  initialResponded = false,
  respondedSummary,
  onRespond,
}: {
  card: GuidanceCardData;
  initialResponded?: boolean;
  respondedSummary?: string;
  onRespond: (optionId: string) => void | Promise<void>;
}) {
  const initialSelection = extractSelectedVersionId(card, respondedSummary);
  const [responded, setResponded] = useState(initialResponded);
  const [modalOpen, setModalOpen] = useState(!initialResponded);
  const [selected, setSelected] = useState<string | null>(
    initialSelection || card.recommended_version || card.version_cards?.[0]?.id || null
  );
  const versions = card.version_cards ?? [];
  const normalizedVersions = versions.map(normalizeSchemeVersion);
  const confirmedVersion = normalizedVersions.find((version) => version.id === initialSelection);
  const summaryText =
    respondedSummary ||
    (confirmedVersion ? `${confirmedVersion.name}：${confirmedVersion.subtitle}` : '已选择');

  const confirmVersion = async (version: SchemeVersionCardData) => {
    setSelected(version.id);
    setResponded(true);
    await Promise.resolve(onRespond(version.id));
    setModalOpen(false);
  };

  const accentClass = (accent?: string) => {
    if (accent === 'violet') return 'from-violet-500 to-fuchsia-500 border-violet-400/40';
    if (accent === 'cyan') return 'from-sky-500 to-cyan-500 border-cyan-400/40';
    return 'from-blue-500 to-sky-500 border-blue-400/40';
  };

  return (
    <>
      <div
        className="rounded-lg border border-[#3a3f4b] bg-[#252526] px-4 py-3 text-[var(--foreground)]"
        data-testid="scheme-version-card"
        data-card-id={card.card_id}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-medium text-cyan-300">
              <Sparkles size={14} />
              <span>{responded ? '三档版本已确认' : '三档版本选择'}</span>
            </div>
            <div className="mt-1 line-clamp-2 text-sm leading-6 text-[var(--foreground-secondary)]">
              {responded ? summaryText : '打开宽屏面板，选择适合当前项目的任务书版本。'}
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              setSelected(initialSelection || card.recommended_version || selected || versions[0]?.id || null);
              setModalOpen(true);
            }}
            className="inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full border border-cyan-400/40 px-3 text-xs font-semibold text-cyan-300 transition hover:bg-cyan-400/10"
          >
            {responded ? <RotateCcw size={13} /> : <ArrowRight size={13} />}
            <span>{responded ? '查看/调整版本' : '查看三档版本'}</span>
          </button>
        </div>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-[80] overflow-y-auto bg-black/84 px-8 py-8 backdrop-blur-sm">
          <div className="mx-auto flex min-h-full w-[min(1480px,calc(100vw-96px))] flex-col">
            <div className="flex items-start justify-between gap-4 px-2 pb-6">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-xs font-medium text-cyan-300">
                  <Sparkles size={14} />
                  <span>版本选择</span>
                </div>
                <h2 className="mt-2 text-xl font-semibold">{card.title || '选择任务书版本'}</h2>
                <p className="mt-1.5 max-w-3xl text-sm leading-6 text-[var(--foreground-secondary)]">
                  {card.prompt_text}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[var(--foreground-secondary)] transition hover:bg-white/8 hover:text-white"
                aria-label="关闭版本选择"
                title="关闭"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex-1">
              <div className="grid gap-5 md:grid-cols-3">
                {normalizedVersions.map((version) => {
                  const recommended = version.id === card.recommended_version || version.recommended;
                  const isSelected = selected === version.id;
                  return (
                    <article
                      key={version.id}
                      onClick={() => setSelected(version.id)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          setSelected(version.id);
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      className={`relative flex min-h-[52rem] flex-col text-left rounded-lg border bg-[#303030] p-6 transition-colors hover:bg-[#363636] ${
                        recommended ? 'border-cyan-400/60' : 'border-[#464646]'
                      } ${isSelected ? 'ring-2 ring-cyan-400/70' : ''}`}
                    >
                      {recommended && (
                        <span className="absolute right-4 top-4 rounded-full bg-cyan-400/15 px-2.5 py-1 text-[11px] font-medium text-cyan-300">
                          推荐
                        </span>
                      )}
                      <div className={`mb-5 inline-flex h-11 w-11 items-center justify-center rounded-lg bg-gradient-to-br ${accentClass(version.accent)}`}>
                        <Sparkles size={20} className="text-white" />
                      </div>
                      <div className="pr-16 text-2xl font-semibold">{version.name}</div>
                      <div className="mt-3 min-h-16 text-sm leading-6 text-[var(--foreground-secondary)]">
                        {version.subtitle}
                      </div>
                      <div className="mt-6 text-white">
                        <span className="text-4xl font-semibold tracking-tight">{version.price_label}</span>
                      </div>
                      <div className="mt-5 space-y-2">
                        <div className="text-xs font-semibold text-[var(--foreground-secondary)]">任务书 17 章目录</div>
                        {(version.directory_preview ?? []).map((item, index) => (
                          <div key={`${version.id}-module-${item}`} className="flex items-start gap-2 text-xs leading-5 text-[var(--foreground-secondary)]">
                            <span className="mt-0.5 w-5 shrink-0 text-[11px] font-semibold text-cyan-300">
                              {String(index + 1).padStart(2, '0')}
                            </span>
                            <span>{item}</span>
                          </div>
                        ))}
                      </div>
                      <div className="mt-5 rounded-lg border border-cyan-400/20 bg-cyan-400/8 p-3">
                        <div className="text-xs font-semibold text-cyan-300">版本差异</div>
                        <div className="mt-2 space-y-2">
                          {getSchemeVersionDifferences(version.id).map((item) => (
                            <div key={`${version.id}-diff-${item}`} className="flex items-start gap-2 text-xs leading-5 text-[var(--foreground-secondary)]">
                              <Check size={13} className="mt-0.5 shrink-0 text-emerald-400" />
                              <span>{item}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="mt-auto pt-6">
                        {isSelected ? (
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              void confirmVersion(version);
                            }}
                            className="inline-flex h-11 w-full items-center justify-center gap-1.5 rounded-full bg-cyan-500 px-5 text-sm font-semibold text-black transition hover:bg-cyan-400"
                          >
                            <span>确认{version.name}</span>
                            <ArrowRight size={15} />
                          </button>
                        ) : (
                          <div className="flex items-center gap-1 text-sm font-semibold text-[var(--foreground-secondary)]">
                            <span>选择{version.name}</span>
                            <ArrowRight size={14} />
                          </div>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function extractSelectedVersionId(card: GuidanceCardData, summary?: string): string | null {
  if (!summary) return null;
  return card.version_cards?.find((version) => summary.includes(version.name))?.id ?? null;
}

function normalizeSchemeVersion(version: SchemeVersionCardData): SchemeVersionCardData {
  if (version.id === 'basic') {
    return { ...version, name: version.name || '基础版', price_label: version.price_label || '99元' };
  }
  if (version.id === 'standard') {
    return { ...version, name: version.name || '标准版', price_label: version.price_label || '499元' };
  }
  if (version.id === 'professional') {
    return { ...version, name: version.name || '高级版', price_label: version.price_label || '2999元' };
  }
  return version;
}

function getSchemeVersionDifferences(versionId: string): string[] {
  if (versionId === 'basic') {
    return [
      '起点模块集：12 个基础模块',
      '自定义模块位：4 个',
      '正式版本数上限：10 个',
      '深度研究：不默认触发，仅支持必要单点事实补缺',
      '多人协作：不支持',
    ];
  }
  if (versionId === 'standard') {
    return [
      '起点模块集：12 个基础模块 + 8 个标准模块',
      '自定义模块位：6 个',
      '正式版本数上限：20 个',
      '深度研究：可在标准模块背后触发',
      '多人协作：不支持',
    ];
  }
  if (versionId === 'professional') {
    return [
      '起点模块集：12 个基础模块 + 8 个标准模块',
      '自定义模块位：10 个',
      '正式版本数上限：30 个',
      '多人协作：支持，权限分级',
      '深度研究：可在标准模块和图谱节点中触发',
    ];
  }
  return [];
}
