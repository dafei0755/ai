import React from 'react';
import Step1ValidationReport from './Step1ValidationReport';

interface ValidationCheck {
  name: string;
  status: 'passed' | 'warning' | 'failed';
  message: string;
  details?: string;
}

interface ValidationReport {
  overall_status: 'passed' | 'warning' | 'failed';
  checks: ValidationCheck[];
  timestamp: string;
}

interface Step1DeepAnalysisProps {
  content: string;
  isLoading?: boolean;
  error?: string;
  validationReport?: ValidationReport;
  onRegenerate?: () => void;
}

const Step1DeepAnalysis: React.FC<Step1DeepAnalysisProps> = ({
  content,
  isLoading = false,
  error,
  validationReport,
  onRegenerate
}) => {
  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12" role="status">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">正在分析您的需求...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6" role="alert">
        <div className="flex items-start gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <h3 className="font-semibold text-red-800 mb-1">分析失败</h3>
            <p className="text-red-600">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (!content || content.trim() === '') {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-12 text-center">
        <span className="text-4xl mb-4 block">📋</span>
        <p className="text-gray-600">暂无分析结果</p>
      </div>
    );
  }

  // Parse sections (v4.0: 支持新旧两种格式)
  const sections = {
    understanding: extractSection(content, '【我们如何理解您的需求】'),
    // v4.0: 优先匹配新格式"深入研究计划"，向后兼容"您将获得什么"
    deliverables: extractSection(content, '【深入研究计划】') || extractSection(content, '【您将获得什么】'),
  };

  // v4.0: 检测是否为新格式（包含"步骤 N"）
  const isNewStepFormat = sections.deliverables ? /步骤\s*\d+/.test(sections.deliverables) : false;

  return (
    <div className="space-y-6">
      {/* Validation Report */}
      {validationReport && (
        <Step1ValidationReport
          report={validationReport}
          onRegenerate={onRegenerate}
        />
      )}

      {/* Section 1: Understanding (融合任务理解与需求分析) */}
      {sections.understanding && (
        <section
          className="bg-gradient-to-r from-indigo-50 to-blue-50 rounded-lg shadow-sm p-4 md:p-6 border border-indigo-100"
          role="region"
          aria-label="我们如何理解您的需求"
        >
          <h2 className="text-xl md:text-2xl font-bold mb-3 md:mb-4 flex items-center gap-2">
            <span className="text-2xl md:text-3xl">🎯</span>
            <span>我们如何理解您的需求</span>
          </h2>
          <div
            className="prose prose-sm md:prose-base max-w-none prose-indigo"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(sections.understanding) }}
          />
        </section>
      )}

      {/* Section 2: Research Plan / Deliverables */}
      {sections.deliverables && (
        <section
          className="bg-white rounded-lg shadow-sm p-4 md:p-6"
          role="region"
          aria-label={isNewStepFormat ? "深入研究计划" : "您将获得什么"}
        >
          <h2 className="text-xl md:text-2xl font-bold mb-3 md:mb-4 flex items-center gap-2">
            <span className="text-2xl md:text-3xl">{isNewStepFormat ? '🔬' : '📦'}</span>
            <span>{isNewStepFormat ? '深入研究计划' : '您将获得什么'}</span>
          </h2>
          <div
            className="prose prose-sm md:prose-base max-w-none"
            dangerouslySetInnerHTML={{ __html: markdownToHtml(sections.deliverables) }}
          />
        </section>
      )}
    </div>
  );
};

// Helper: Extract section content between headers
function extractSection(content: string, header: string): string | null {
  // v4.0: 支持新旧两种 header 格式
  const headerRegex = new RegExp(`\\*\\*${header}\\*\\*([\\s\\S]*?)(?=\\*\\*【|$)`, 'i');
  const match = content.match(headerRegex);
  return match ? match[1].trim() : null;
}

// Helper: Convert markdown to HTML (v4.0: 支持"步骤 N"格式 + 旧 emoji 格式)
function markdownToHtml(markdown: string): string {
  let html = markdown;

  // v4.0: 处理"步骤 N"格式标题
  html = html.replace(/^步骤\s*(\d+)\s+(.+)$/gm,
    '<h3 class="text-lg font-bold mt-6 mb-3 flex items-center gap-2"><span class="inline-flex items-center justify-center w-7 h-7 rounded-full bg-blue-100 text-blue-700 text-sm font-bold">$1</span><span>$2</span></h3>');

  // 1. 处理标题（带emoji的数字标题 — 旧格式兼容）
  html = html.replace(/^(\d️⃣)\s+\*\*(.+?)\*\*\s*（约(.+?)页）/gm,
    '<h3 class="text-lg font-bold mt-6 mb-3 flex items-center gap-2"><span class="text-2xl">$1</span><span>$2</span><span class="text-sm text-gray-500 font-normal ml-2">（约$3页）</span></h3>');

  // 2. 处理粗体文本
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold">$1</strong>');

  // 3. 处理列表项（保持原有emoji）
  html = html.replace(/^•\s+(.+)$/gm, '<li class="ml-4 mb-2">• $1</li>');
  html = html.replace(/^✓\s+(.+)$/gm, '<li class="ml-4 mb-2 text-green-700">✓ $1</li>');
  html = html.replace(/^✅\s+(.+)$/gm, '<li class="ml-4 mb-2 text-blue-700">✅ $1</li>');
  // v4.0: 处理 - 开头的列表项
  html = html.replace(/^-\s+(.+)$/gm, '<li class="ml-4 mb-2">$1</li>');

  // 4. 处理段落分隔
  html = html.replace(/\n\n+/g, '</p><p class="mb-3">');

  // 5. 包裹段落标签
  html = '<p class="mb-3">' + html + '</p>';

  // 6. 清理空段落
  html = html.replace(/<p class="mb-3">\s*<\/p>/g, '');

  // 7. 处理列表包裹
  html = html.replace(/(<li[^>]*>[\s\S]*?<\/li>)/g, '<ul class="list-none space-y-1 my-3">$1</ul>');

  return html;
}

export default Step1DeepAnalysis;
