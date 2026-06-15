'use client';

export interface ApprovedKnowledgeCard {
  card_id: string;
  title: string;
  status: string;
  summary?: string;
  evidence_level?: string;
  evidence_strength?: string;
  knowledge_status?: string;
  source_role?: string;
  package_ids?: string[];
  ontology_dimension_ids?: string[];
  allowed_use?: string[];
  not_allowed_use?: string[];
  output_usage?: string[];
  task_brief_chapter?: string[];
  v33_complete?: boolean;
  missing_v33_fields?: string[];
}

export interface ApprovedKnowledgeCardSummary {
  approved_card_count: number;
  v33_complete_count: number;
  missing_v33_field_count: number;
  package_with_cards_count: number;
}

export function ApprovedKnowledgeCardsPanel({
  loading,
  cards,
  summary,
  onReload,
}: {
  loading: boolean;
  cards: ApprovedKnowledgeCard[];
  summary?: ApprovedKnowledgeCardSummary;
  onReload: () => void;
}) {
  const renderPills = (items: string[] | undefined, tone: 'blue' | 'green' | 'red' | 'purple' | 'gray') => {
    const toneClass = {
      blue: 'bg-blue-50 text-blue-700 border-blue-100',
      green: 'bg-green-50 text-green-700 border-green-100',
      red: 'bg-red-50 text-red-700 border-red-100',
      purple: 'bg-purple-50 text-purple-700 border-purple-100',
      gray: 'bg-gray-50 text-gray-700 border-gray-100',
    }[tone];
    if (!items || items.length === 0) {
      return <span className="text-xs text-gray-400">-</span>;
    }
    return (
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <span key={item} className={`px-2 py-1 text-xs rounded border ${toneClass}`}>
            {item}
          </span>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold">Approved Knowledge Cards</h2>
          <p className="text-sm text-gray-600 mt-1">
            只展示已审核通过、可被 context_packet 和方案高参运行时召回的知识卡。
          </p>
        </div>
        <button
          onClick={onReload}
          disabled={loading}
          className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:bg-gray-300"
        >
          刷新
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">已审核卡</div>
          <div className="text-2xl font-bold text-blue-600">{summary?.approved_card_count ?? cards.length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">v3.3 完整</div>
          <div className="text-2xl font-bold text-green-600">{summary?.v33_complete_count ?? cards.filter((card) => card.v33_complete).length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">缺失字段</div>
          <div className="text-2xl font-bold text-red-600">{summary?.missing_v33_field_count ?? 0}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="text-sm text-gray-600">覆盖知识包</div>
          <div className="text-2xl font-bold text-purple-600">{summary?.package_with_cards_count ?? 0}</div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-8 text-gray-600">正在加载已审核知识卡...</div>
      ) : cards.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {cards.map((card) => (
            <article key={card.card_id} className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-gray-900">{card.title}</h3>
                  <p className="text-xs font-mono text-gray-500 mt-1">{card.card_id}</p>
                </div>
                <span className={`shrink-0 px-2 py-1 text-xs rounded border ${
                  card.v33_complete
                    ? 'bg-green-50 text-green-700 border-green-200'
                    : 'bg-amber-50 text-amber-700 border-amber-200'
                }`}>
                  {card.v33_complete ? 'v3.3 完整' : '字段缺失'}
                </span>
              </div>

              {card.summary && <p className="text-sm text-gray-700">{card.summary}</p>}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div>
                  <div className="text-gray-500 mb-1">知识包</div>
                  {renderPills(card.package_ids, 'blue')}
                </div>
                <div>
                  <div className="text-gray-500 mb-1">本体维度</div>
                  {renderPills(card.ontology_dimension_ids, 'purple')}
                </div>
                <div>
                  <div className="text-gray-500 mb-1">允许用途</div>
                  {renderPills(card.allowed_use, 'green')}
                </div>
                <div>
                  <div className="text-gray-500 mb-1">禁止用途</div>
                  {renderPills(card.not_allowed_use, 'red')}
                </div>
                <div>
                  <div className="text-gray-500 mb-1">输出入口</div>
                  {renderPills(card.output_usage, 'gray')}
                </div>
                <div>
                  <div className="text-gray-500 mb-1">任务书章节</div>
                  {renderPills(card.task_brief_chapter, 'gray')}
                </div>
              </div>

              <div className="flex flex-wrap gap-2 text-xs text-gray-600">
                <span className="px-2 py-1 bg-gray-50 rounded">status: {card.status}</span>
                {card.knowledge_status && <span className="px-2 py-1 bg-gray-50 rounded">knowledge: {card.knowledge_status}</span>}
                {card.source_role && <span className="px-2 py-1 bg-gray-50 rounded">role: {card.source_role}</span>}
                {card.evidence_level && <span className="px-2 py-1 bg-gray-50 rounded">evidence: {card.evidence_level}</span>}
                {card.evidence_strength && <span className="px-2 py-1 bg-gray-50 rounded">strength: {card.evidence_strength}</span>}
              </div>

              {!card.v33_complete && card.missing_v33_fields && card.missing_v33_fields.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-800">
                  缺失 v3.3 字段：{card.missing_v33_fields.join(', ')}
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">暂无已审核知识卡</div>
      )}
    </div>
  );
}
