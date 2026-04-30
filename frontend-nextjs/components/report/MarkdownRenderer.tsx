// components/report/MarkdownRenderer.tsx
// 增强的Markdown渲染器组件

'use client';

import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import { Copy, Check, ExternalLink } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

// 🎯 自定义代码块组件
const CodeBlock: React.FC<{ 
  children: React.ReactNode; 
  className?: string; 
  inline?: boolean;
}> = ({ children, className, inline }) => {
  const [copied, setCopied] = React.useState(false);
  
  const language = className?.replace('language-', '') || 'text';
  const isInline = inline || !className;
  
  const copyToClipboard = async () => {
    if (typeof children === 'string') {
      await navigator.clipboard.writeText(children);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (isInline) {
    return (
      <code className="bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded text-sm font-mono">
        {children}
      </code>
    );
  }

  return (
    <div className="relative group">
      <div className="flex items-center justify-between bg-slate-800 px-4 py-2 rounded-t-lg border border-slate-700">
        <span className="text-sm text-gray-400 font-medium">{language}</span>
        <button
          onClick={copyToClipboard}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
        >
          {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="bg-slate-900 p-4 rounded-b-lg border border-t-0 border-slate-700 overflow-x-auto">
        <code className="text-gray-300 text-sm font-mono leading-relaxed">
          {children}
        </code>
      </pre>
    </div>
  );
};

// 🎯 自定义链接组件
const CustomLink: React.FC<{ 
  href?: string; 
  children: React.ReactNode;
}> = ({ href, children }) => {
  const isExternal = href?.startsWith('http') || href?.startsWith('https');
  
  return (
    <a
      href={href}
      target={isExternal ? '_blank' : '_self'}
      rel={isExternal ? 'noopener noreferrer' : undefined}
      className="text-blue-400 hover:text-blue-300 underline decoration-blue-400/50 hover:decoration-blue-300 transition-colors inline-flex items-center gap-1"
    >
      {children}
      {isExternal && <ExternalLink className="w-3 h-3" />}
    </a>
  );
};

// 🎯 自定义表格组件
const CustomTable: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="overflow-x-auto my-4">
    <table className="min-w-full bg-slate-800/50 border border-slate-700 rounded-lg">
      {children}
    </table>
  </div>
);

// 🎯 自定义引用块组件
const CustomBlockquote: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <blockquote className="border-l-4 border-blue-500 bg-blue-500/10 pl-6 py-4 my-4 italic text-gray-300">
    {children}
  </blockquote>
);

// 🎯 增强的Markdown渲染器
const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ 
  content, 
  className = "" 
}) => {
  // 预处理内容
  const processedContent = useMemo(() => {
    if (!content) return '';
    
    return content
      // 标准化换行符
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      // 处理转义字符
      .replace(/\\n\\n/g, '\n\n')
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      // 修复可能的Markdown格式问题
      .replace(/([。！？])(\s*)([#])/g, '$1\n\n$3') // 句号后的标题
      .replace(/([#]+)\s*$/gm, '$1 ') // 确保标题有文本
      // 修复列表格式
      .replace(/([。！？])(\s*)([-*+])/g, '$1\n\n$3')
      .trim();
  }, [content]);

  const components = {
    // 标题组件 - 带自定义样式
    h1: ({ children, ...props }: any) => (
      <h1 className="text-2xl font-bold text-white mt-8 mb-4 pb-3 border-b-2 border-gradient-to-r from-blue-500 to-purple-500 bg-gradient-to-r from-blue-500/10 to-purple-500/10 px-4 py-3 rounded-t-lg" {...props}>
        {children}
      </h1>
    ),
    h2: ({ children, ...props }: any) => (
      <h2 className="text-xl font-semibold text-blue-300 mt-6 mb-3 border-b-2 border-blue-500/50 pb-2" {...props}>
        {children}
      </h2>
    ),
    h3: ({ children, ...props }: any) => (
      <h3 className="text-lg font-semibold text-purple-300 mt-5 mb-3 border-l-4 border-purple-500 pl-4 bg-purple-500/10 py-2 rounded-r" {...props}>
        {children}
      </h3>
    ),
    h4: ({ children, ...props }: any) => (
      <h4 className="text-base font-medium text-cyan-300 mt-4 mb-2 border-l-2 border-cyan-500 pl-3" {...props}>
        {children}
      </h4>
    ),
    h5: ({ children, ...props }: any) => (
      <h5 className="text-sm font-medium text-gray-300 mt-3 mb-2" {...props}>
        {children}
      </h5>
    ),
    h6: ({ children, ...props }: any) => (
      <h6 className="text-xs font-medium text-gray-400 mt-2 mb-1 uppercase tracking-wider" {...props}>
        {children}
      </h6>
    ),

    // 段落组件
    p: ({ children, ...props }: any) => (
      <p className="text-sm text-gray-300 leading-[1.8] mb-4 text-justify" {...props}>
        {children}
      </p>
    ),

    // 列表组件
    ul: ({ children, ...props }: any) => (
      <ul className="space-y-2 mb-4 pl-0 list-none" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }: any) => (
      <ol className="space-y-2 mb-4 pl-4 list-decimal list-inside" {...props}>
        {children}
      </ol>
    ),
    li: ({ children, ...props }: any) => (
      <li className="text-sm text-gray-300 leading-relaxed pl-0" {...props}>
        {children}
      </li>
    ),

    // 代码组件
    code: CodeBlock,
    pre: ({ children }: any) => children, // pre 由 CodeBlock 处理

    // 链接组件
    a: CustomLink,

    // 表格组件
    table: CustomTable,
    th: ({ children, ...props }: any) => (
      <th className="px-4 py-2 text-left text-sm font-semibold text-gray-200 bg-slate-700 border-b border-slate-600" {...props}>
        {children}
      </th>
    ),
    td: ({ children, ...props }: any) => (
      <td className="px-4 py-2 text-sm text-gray-300 border-b border-slate-700" {...props}>
        {children}
      </td>
    ),

    // 引用块
    blockquote: CustomBlockquote,

    // 分割线
    hr: (props: any) => (
      <hr className="my-6 border-gray-600" {...props} />
    ),

    // 强调文本
    strong: ({ children, ...props }: any) => (
      <strong className="font-semibold text-white" {...props}>
        {children}
      </strong>
    ),
    em: ({ children, ...props }: any) => (
      <em className="italic text-gray-200" {...props}>
        {children}
      </em>
    ),
  };

  if (!processedContent) {
    return <div className="text-gray-400 text-sm">暂无内容</div>;
  }

  return (
    <div className={`markdown-content text-content-optimized ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, rehypeSanitize]}
        components={components as any}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;