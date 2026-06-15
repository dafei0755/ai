// lib/conceptExtractor.ts
// 从中文对话 / 分析文本中提取概念词条与共现边
// Copilot 生成 2026-03-15（v5 重写：Intl.Segmenter + 领域词表前扫 + 全局滑动窗口）

export interface ConceptNode {
  id: string;
  label: string;
  cluster: string;   // 初始为 'default'；Louvain 运行后由 SchemeGraph 覆写
  freq: number;      // 词频（跨多次 ingestText 累积）
}

export type EdgeRelType = 'association' | 'causal' | 'hierarchical' | 'conflict';

export interface CooccurrenceEdge {
  source: string;   // node id
  target: string;   // node id
  weight: number;   // 共现次数
  isConflict: boolean;
  relType: EdgeRelType;
}

// ─── 停用词：虚词 + 极泛化动词 ───────────────────────────────────────────────
const STOPWORDS = new Set<string>([
  // 单字功能词
  '的','地','得','了','啊','吗','呢','吧','呀','嗯',
  '以','与','和','或','在','是','为','从','到','于','对','向','等',
  '被','把','让','使','按','借','依','当','虽','而','且','因','故',
  '其','之','中','上','下','内','外','后','前','不','也','都','就',
  '很','更','最','太','有','无','他','她','它','我','你','这','那',
  // 双字/多字虚词
  '我们','你们','他们','这个','那个','这些','那些',
  '可以','如果','因为','所以','但是','然后','还是','已经','正在',
  '需要','通过','进行','对于','关于','以及','还有','什么','怎么',
  '为什么','应该','必须','希望','感觉','觉得','认为','表示',
  '方面','方式','情况','问题','过程','结果','内容','方向','目标',
  '基础','能够','可能','比较','整体','具体','实现','提供','包括',
  '形成','发展','考虑','满足','达到','体现','强调','注重','确保',
  '避免','主要','重要','关键','核心','整个','不同','相关','更加',
  '同时','其中','之间','之外','以上','以下','以内','本身','一个',
  // 系统/日志/流程状态词（防止 node_update.detail 污染）
  '分析','建议','说明','请','为了','概念','提供','组织',
  '完整','提出','输出','阶段','流程','运行','执行','完成',
  // 极泛化描述词（在设计语境中几乎每句都出现，无区分性）
  '设计','方案','项目','用户','空间','需要',
  // Segmenter 常见误判碎片（domain word 被切断后的残片）
  '受潮','调消费','建客','活方','方式',
]);

// ─── 领域词表：设计 / 文化 / 用户 复合词（通用分词器不认识的词）────────────────
const DOMAIN_WORDS: string[] = [
  // 亚文化 / 潮流
  '潮玩','潮流文化','街头文化','潮牌','联名款','赛博朋克','蒸汽波',
  // 用户群体
  '富二代','00后','90后','高净值','中产阶级','新贵族',
  // 消费 / 身份
  '消费文化','品牌文化','身份认同','消费升级','符号消费',
  // 空间 / 设计风格
  '极简主义','功能主义','包豪斯','侘寂','北欧风','工业风',
  '新中式','奶油风','反差美学','空间叙事','光影设计','材质肌理',
  '装置艺术','空间语言','视觉张力',
  // 张力 / 洞察（interrupt 高频词）
  '高调表达','内在深度','长久价值','私密遮掩','情感联结',
  '文化脉络','隐性奢侈','身份诉求',
  // 定制 / 档次
  '高端定制','私人定制','隐奢','轻奢','极奢','全定制',
  // 品牌
  'HAY','MUJI','Hermès','Vitra','Moooi',
];

// ─── DOMAIN_WORDS 按长度降序排序（优先匹配长词，避免短词抢占）────────────────
const DOMAIN_WORDS_SORTED = [...DOMAIN_WORDS].sort((a, b) => b.length - a.length);

// ─── Segmenter 单例（避免每次调用重建）─────────────────────────────────────────
const zhSegmenter: Intl.Segmenter | null =
  typeof Intl !== 'undefined' && 'Segmenter' in Intl
    ? new (Intl as any).Segmenter('zh-CN', { granularity: 'word' })
    : null;

// ─── 冲突触发词 ────────────────────────────────────────────────────────────────
const CONFLICT_SIGNALS = ['矛盾','冲突','张力','vs','VS','对立','取舍','权衡','然而','难以'];

// ─── 因果触发词 ────────────────────────────────────────────────────────────────
const CAUSAL_SIGNALS = [
  '导致','因此','所以','从而','使得','产生','推动','影响','决定',
  '引发','造成','促进','带来','触发','依赖','决策','结果','后果',
];

// ─── 层次/包含触发词 ────────────────────────────────────────────────────────────
const HIERARCHICAL_SIGNALS = [
  '包括','包含','分为','分成','属于','构成','组成','涵盖','覆盖',
  '下设','类型','包括以下','主要有','分类为','子系统','其中有',
];

function isCausalSentence(s: string): boolean {
  return CAUSAL_SIGNALS.some(sig => s.includes(sig));
}

function isHierarchicalSentence(s: string): boolean {
  return HIERARCHICAL_SIGNALS.some(sig => s.includes(sig));
}

// ─── 文本切分：按主要断句标点分句（不在逗号处切断，保留同句内共现机会）──────────
function splitSentences(text: string): string[] {
  return text
    .split(/[。！？\n；;.!?]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 1);
}

/**
 * extractWords v5 — 领域词前扫（位置标记）+ Intl.Segmenter 后处理
 *
 * 策略：
 * 1. 先扫描 DOMAIN_WORDS，找到则加入结果，并标记占用字符位置
 * 2. 再用 Segmenter 遍历，跳过已被领域词占用的 token
 * 3. 对 Segmenter 输出的 ≥2 字词进行 STOPWORDS 过滤
 */
function extractWords(sentence: string): string[] {
  const result = new Set<string>();

  // ASCII 专有名词（如 HAY, LED, AI）
  sentence.match(/[A-Z][A-Za-z0-9]{1,}/g)?.forEach((w) => result.add(w));

  // 领域词前扫 + 位置占用标记
  const consumed = new Uint8Array(sentence.length);
  for (const dw of DOMAIN_WORDS_SORTED) {
    let idx = sentence.indexOf(dw);
    while (idx !== -1) {
      result.add(dw);
      for (let k = idx; k < idx + dw.length; k++) consumed[k] = 1;
      idx = sentence.indexOf(dw, idx + 1);
    }
  }

  // Intl.Segmenter（跳过已被领域词占用的 token）
  if (zhSegmenter) {
    let charPos = 0;
    for (const { segment, isWordLike } of (zhSegmenter as any).segment(sentence)) {
      const start = charPos;
      charPos += segment.length;
      if (!isWordLike) continue;
      // 如果 segment 的起始或中间字符已被领域词占用，跳过
      let dominated = false;
      for (let k = start; k < start + segment.length; k++) {
        if (consumed[k]) { dominated = true; break; }
      }
      if (dominated) continue;
      const t = segment.trim();
      if (t.length >= 2 && !STOPWORDS.has(t)) result.add(t);
    }
  }

  return [...result].filter((t) => t.length >= 2 && !STOPWORDS.has(t));
}

function isConflictSentence(sentence: string): boolean {
  return CONFLICT_SIGNALS.some((sig) => sentence.includes(sig));
}

// ─── 主 API ───────────────────────────────────────────────────────────────────

export interface IngestResult {
  termFreqs: Map<string, number>;
  edges: CooccurrenceEdge[];
}

/** 从 term 文本生成稳定节点 ID */
export function termId(term: string): string {
  return `t_${term.replace(/[^A-Za-z\u4e00-\u9fff]/g, '_')}`;
}

/**
 * ingestText v6 — 全局滑动窗口共现 + 关系类型识别
 *
 * 关系类型优先级：conflict > causal > hierarchical > association
 * - 冲突句中的词对 → conflict
 * - 因果句中的词对 → causal
 * - 层次/包含句中的词对 → hierarchical
 * - 其余 → association
 */
export function ingestText(text: string): IngestResult {
  type EdgeEntry = { w: number; c: boolean; causal: boolean; hier: boolean };
  const termFreqs = new Map<string, number>();
  const edgeMap   = new Map<string, EdgeEntry>();

  if (!text || text.trim().length < 2) return { termFreqs, edges: [] };

  const sentences = splitSentences(text);

  // 构建全局词序列，记录各类触发句中的词的 index
  const allTerms: string[]  = [];
  const conflictIdx          = new Set<number>();
  const causalIdx            = new Set<number>();
  const hierIdx              = new Set<number>();

  for (const sent of sentences) {
    const terms = extractWords(sent);
    if (terms.length === 0) continue;
    const startIdx = allTerms.length;
    for (const t of terms) {
      termFreqs.set(t, (termFreqs.get(t) ?? 0) + 1);
      allTerms.push(t);
    }
    if (isConflictSentence(sent))    for (let i = startIdx; i < allTerms.length; i++) conflictIdx.add(i);
    if (isCausalSentence(sent))      for (let i = startIdx; i < allTerms.length; i++) causalIdx.add(i);
    if (isHierarchicalSentence(sent)) for (let i = startIdx; i < allTerms.length; i++) hierIdx.add(i);
  }

  // 全局滑窗共现（window=7，跨句）
  const WINDOW = 7;
  for (let i = 0; i < allTerms.length; i++) {
    for (let j = i + 1; j < Math.min(i + WINDOW + 1, allTerms.length); j++) {
      if (allTerms[i] === allTerms[j]) continue;
      const [a, b] = allTerms[i] < allTerms[j]
        ? [allTerms[i], allTerms[j]]
        : [allTerms[j], allTerms[i]];
      const key   = `${a}|||${b}`;
      const prev  = edgeMap.get(key) ?? { w: 0, c: false, causal: false, hier: false };
      edgeMap.set(key, {
        w:     prev.w + 1,
        c:     prev.c     || conflictIdx.has(i) || conflictIdx.has(j),
        causal: prev.causal || causalIdx.has(i)  || causalIdx.has(j),
        hier:  prev.hier   || hierIdx.has(i)     || hierIdx.has(j),
      });
    }
  }

  const edges: CooccurrenceEdge[] = [];
  edgeMap.forEach(({ w, c, causal, hier }, key) => {
    const [src, tgt] = key.split('|||');
    let relType: EdgeRelType = 'association';
    if (c)      relType = 'conflict';
    else if (causal) relType = 'causal';
    else if (hier)   relType = 'hierarchical';
    edges.push({
      source:     termId(src),
      target:     termId(tgt),
      weight:     w,
      isConflict: c,
      relType,
    });
  });

  return { termFreqs, edges };
}

//  从 interrupt_data 提取 pending 节点 

export interface InterruptConceptNode extends ConceptNode {
  source: 'tension' | 'dimension' | 'gap';
}

export function extractConceptsFromInterruptData(interruptData: any): InterruptConceptNode[] {
  if (!interruptData) return [];

  interface RawEntry { label: string; source: InterruptConceptNode['source'] }
  const raw: RawEntry[] = [];

  const tensions: string[] = interruptData.core_tensions ?? [];
  tensions.forEach((t) => raw.push({ label: String(t).trim(), source: 'tension' }));

  const identified: any[] = interruptData.already_identified ?? [];
  identified.forEach((d) => {
    const label = typeof d === 'string' ? d : d?.name ?? d?.dimension ?? JSON.stringify(d);
    raw.push({ label: String(label).trim(), source: 'dimension' });
  });

  const missing: string[] = interruptData.missing_information ?? [];
  missing.forEach((m) => raw.push({ label: String(m).trim(), source: 'gap' }));

  return raw
    .filter(({ label }) => label.length >= 2)
    .map(({ label, source }, idx) => ({
      id: `interrupt_${source}_${idx}_${label.slice(0, 10).replace(/\s+/g, '_')}`,
      label: label.slice(0, 30),
      cluster: 'default',
      freq: 1,
      source,
    }));
}
