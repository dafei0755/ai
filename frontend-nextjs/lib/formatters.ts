// lib/formatters.ts
// 🔥 v7.6: 统一的格式化工具函数
// 集中管理所有格式化逻辑，避免重复实现导致的不一致

/**
 * 格式化专家名称为友好显示
 * 
 * 支持三种输入格式：
 * 1. 动态名称格式（后端已处理）: "4-1 设计研究员" → 直接返回
 * 2. Role ID 完整格式: "V4_设计研究员_4-1" → 转换为 "4-1 设计研究员"
 * 3. Role ID 简单格式: "V4_设计研究员" → 转换为 "设计研究员"
 * 
 * @example
 * formatExpertName("4-1 设计研究员")     // → "4-1 设计研究员"
 * formatExpertName("V4_设计研究员_4-1")  // → "4-1 设计研究员"
 * formatExpertName("V4_设计研究员")      // → "设计研究员"
 */
export function formatExpertName(rawName: string): string {
  if (!rawName) return '未知专家';
  
  // 检测是否已经是动态名称格式（数字-数字 开头）
  if (/^\d+-\d+\s/.test(rawName)) {
    return rawName;
  }
  
  // 匹配 Role ID 完整模式: V{层级}_{角色名称}_{子角色编号}
  const match = rawName.match(/^V(\d)_(.+?)_(\d+-\d+)$/);
  if (match) {
    const [, , roleName, subId] = match;
    return `${subId} ${roleName}`;
  }
  
  // 备用模式: V{层级}_{角色名称}（无子角色编号）
  const fallbackMatch = rawName.match(/^V(\d)_(.+)$/);
  if (fallbackMatch) {
    return fallbackMatch[2];
  }
  
  return rawName;
}

/**
 * 从专家名称提取层级（V2-V6）
 * 用于颜色映射等场景
 * 
 * @example
 * getExpertLevel("V4_设计研究员_4-1")  // → 4
 * getExpertLevel("4-1 设计研究员")     // → 4
 */
export function getExpertLevel(expertName: string): number {
  // Role ID 格式
  const vMatch = expertName.match(/V(\d)/);
  if (vMatch) {
    return parseInt(vMatch[1], 10);
  }
  
  // 动态名称格式：从 "4-1 xxx" 提取层级 4
  const dynamicMatch = expertName.match(/^(\d)-/);
  if (dynamicMatch) {
    return parseInt(dynamicMatch[1], 10);
  }
  
  return 2; // 默认 V2
}

/**
 * 格式化日期时间
 */
export function formatDateTime(date: string | Date | null | undefined): string | null {
  if (!date) return null;
  try {
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return null;
  }
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
