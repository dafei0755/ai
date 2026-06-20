const TITLE_STORAGE_CHARS = 120;
const MIN_SUMMARY_CHARS = 12;

const normalizeTitleSource = (input: string) =>
  input
    .replace(/\s+/g, ' ')
    .trim();

const compactTitleForCompare = (input: string) =>
  normalizeTitleSource(input).replace(/[，。！？、；：,.!?;:"“”'‘’（）()【】\[\]{}<>《》\s]/g, '');

const charLength = (value: string) => Array.from(value).length;

const limitChars = (value: string, max = TITLE_STORAGE_CHARS) => {
  const chars = Array.from(value);
  if (chars.length <= max) return value;
  return `${chars.slice(0, max).join('')}…`;
};

export const limitSessionTitle = (title: string) => limitChars(normalizeTitleSource(title), TITLE_STORAGE_CHARS);

const isWeakExplicitTitle = (title: string) => {
  const normalized = compactTitleForCompare(title);
  if (!normalized) return true;
  if (charLength(normalized) < MIN_SUMMARY_CHARS) return true;
  if (/(需求摘要|项目方案建议梳理|优化建议梳理|分析建议梳理)$/.test(normalized)) return true;
  return /^(深圳|商业|空间|资源|预算|方案|项目)?(方案建议|优化建议|分析建议|预算|设计|分类)$/.test(normalized);
};

const isStalePrefixTitle = (rawInput: string, title: string) => {
  const normalizedRaw = compactTitleForCompare(rawInput);
  const normalizedTitle = compactTitleForCompare(title);
  if (!normalizedRaw || !normalizedTitle) return false;
  if (normalizedRaw === normalizedTitle) return false;
  return normalizedRaw.startsWith(normalizedTitle);
};

export const deriveSessionTitle = (input: string): string => {
  const source = limitSessionTitle(input);
  return source || '未命名项目';
};

export const resolveSessionTitle = (rawInput: string, displayName?: string | null): string => {
  const explicit = displayName?.trim() ?? '';
  if (explicit && rawInput && isStalePrefixTitle(rawInput, explicit)) return deriveSessionTitle(rawInput);
  if (explicit && !isWeakExplicitTitle(explicit)) return limitSessionTitle(explicit);
  return deriveSessionTitle(rawInput || explicit);
};
