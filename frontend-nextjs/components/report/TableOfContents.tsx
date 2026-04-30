// components/report/TableOfContents.tsx
// 章节导航组件

'use client';

import { FC, useState, useEffect } from 'react';
import { List, ChevronRight } from 'lucide-react';
import { StructuredReport } from '@/types';

interface TableOfContentsProps {
  report: StructuredReport;
  onSectionClick?: (sectionId: string) => void;
}

interface TocItem {
  id: string;
  title: string;
  type: 'main' | 'section' | 'expert';
}

const TableOfContents: FC<TableOfContentsProps> = ({ report, onSectionClick }) => {
  const [activeSection, setActiveSection] = useState<string>('user-question');
  const [isCollapsed, setIsCollapsed] = useState(false);

  // 构建目录项 - v7.0 简化结构（5章节）
  const tocItems: TocItem[] = [
    { id: 'user-question', title: '用户原始需求', type: 'main' },
    { id: 'questionnaire-responses', title: '校准问卷', type: 'main' },
    { id: 'requirements-analysis', title: '需求分析结果', type: 'main' },
    // { id: 'insights', title: '需求洞察（综合）', type: 'main' },  // 已取消
    { id: 'core-answer', title: '核心答案', type: 'main' },
    { id: 'expert-reports', title: '专家报告附录', type: 'main' },
  ];

  // 滚动到指定章节
  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveSection(sectionId);
      if (onSectionClick) {
        onSectionClick(sectionId);
      }
    }
  };

  // 监听滚动，更新当前活动章节
  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY + 100;

      for (const item of tocItems) {
        const element = document.getElementById(item.id);
        if (element) {
          const { offsetTop, offsetHeight } = element;
          if (scrollPosition >= offsetTop && scrollPosition < offsetTop + offsetHeight) {
            setActiveSection(item.id);
            break;
          }
        }
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [tocItems]);

  return (
    <div className={`bg-[var(--card-bg)] border border-[var(--border-color)] rounded-xl overflow-hidden transition-all ${isCollapsed ? 'w-12' : 'w-64'}`}>
      {/* 头部 */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full px-4 py-3 flex items-center justify-between border-b border-[var(--border-color)] hover:bg-[var(--sidebar-bg)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <List className="w-4 h-4 text-gray-400" />
          {!isCollapsed && <span className="text-sm font-medium text-white">章节导航</span>}
        </div>
        {!isCollapsed && (
          <ChevronRight className={`w-4 h-4 text-gray-400 transition-transform ${isCollapsed ? '' : 'rotate-180'}`} />
        )}
      </button>

      {/* 目录列表 */}
      {!isCollapsed && (
        <nav className="p-2 max-h-[calc(100vh-200px)] overflow-y-auto">
          <ul className="space-y-1">
            {tocItems.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => scrollToSection(item.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    activeSection === item.id
                      ? 'bg-[var(--primary)]/20 text-[var(--primary)]'
                      : 'text-gray-400 hover:text-white hover:bg-[var(--sidebar-bg)]'
                  } ${item.type === 'section' ? 'pl-6 text-xs' : ''}`}
                >
                  {item.title}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </div>
  );
};

export default TableOfContents;
