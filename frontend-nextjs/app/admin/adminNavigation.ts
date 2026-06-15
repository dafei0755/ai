export type AdminNavItem = {
  href: string;
  icon: string;
  label: string;
  external?: boolean;
};

export const adminPrimaryLinks: AdminNavItem[] = [
  { href: '/admin/dashboard', icon: '📊', label: '仪表板' },
  { href: '/admin/monitoring', icon: '📈', label: '系统监控' },
  { href: '/admin/database', icon: '🗄️', label: '数据库监控' },
  { href: '/admin/sessions', icon: '💬', label: '会话管理' },
  { href: '/admin/conversations', icon: '💬', label: '对话分析' },
  { href: '/admin/users', icon: '👥', label: '用户分析' },
  { href: '/admin/tools', icon: '🔎', label: '搜索工具' },
  { href: '/admin/search-filters', icon: '🛡️', label: '搜索过滤器' },
  { href: '/admin/knowledge-base', icon: '📚', label: '知识库管理' },
  { href: '/admin/capability-boundary', icon: '⚠️', label: '能力边界监控' },
  { href: '/admin/concept-maps', icon: '🎨', label: '概念图' },
  { href: '/admin/dimension-learning', icon: '🧠', label: '维度学习' },
  { href: '/admin/learning-center', icon: '🔁', label: '自学习中心' },
  { href: '/admin/review-queue', icon: '✅', label: '治理复核中心' },
  { href: '/admin/project-types', icon: '🏷️', label: '项目类型管理' },
  { href: '/admin/space-classification', icon: '🧭', label: '空间分类' },
  { href: '/admin/ontology', icon: '🔷', label: '动态本体论' },
  { href: '/admin/ontology/review', icon: '✅', label: '本体论扩展审核' },
];

export const showcaseLinks: AdminNavItem[] = [
  { href: '/showcase', icon: '🎬', label: '展示页面', external: true },
  { href: '/admin/showcase-config', icon: '⚙️', label: '展示配置' },
];
