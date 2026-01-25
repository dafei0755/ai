/**
 * SearchReferencesDisplay 组件单元测试
 * 测试搜索引用展示功能（v7.120 修复验证）
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SearchReferencesDisplay } from '../components/report/SearchReferencesDisplay';
import type { SearchReference } from '../types';

describe('SearchReferencesDisplay', () => {
  const mockReferences: SearchReference[] = [
    {
      source_tool: 'tavily',
      title: 'Modern Interior Design Trends 2024',
      url: 'https://example.com/article1',
      snippet: 'Latest trends in modern interior design focusing on minimalism and sustainability.',
      relevance_score: 0.95,
      quality_score: 85,
      deliverable_id: '2-1_1_143022_abc',
      query: 'modern interior design trends',
      timestamp: '2025-01-03T10:00:00Z',
      llm_relevance_score: 92,
      llm_scoring_reason: 'Highly relevant to user requirements'
    },
    {
      source_tool: 'arxiv',
      title: 'Architectural Psychology Research Paper',
      url: 'https://arxiv.org/abs/12345',
      snippet: 'Research on the psychological impact of architectural spaces on human behavior.',
      relevance_score: 0.88,
      deliverable_id: '3-1_2_143023_def',
      query: 'architectural psychology',
      timestamp: '2025-01-03T10:05:00Z'
    },
    {
      source_tool: 'bocha',
      title: '办公空间设计案例',
      snippet: '现代办公空间的设计理念和实施案例分享。',
      relevance_score: 0.92,
      deliverable_id: '4-1_3_143024_ghi',
      query: '办公空间设计',
      timestamp: '2025-01-03T10:10:00Z'
    }
  ];

  test('should not render when references array is empty', () => {
    const { container } = render(<SearchReferencesDisplay references={[]} />);
    expect(container.firstChild).toBeNull();
  });

  test('should not render when references is null/undefined', () => {
    const { container } = render(<SearchReferencesDisplay references={null as any} />);
    expect(container.firstChild).toBeNull();
  });

  test('should render search references heading with count', () => {
    render(<SearchReferencesDisplay references={mockReferences} />);
    expect(screen.getByText(/搜索引用/)).toBeInTheDocument();
    expect(screen.getByText(/\(3 条\)/)).toBeInTheDocument();
  });

  test('should group references by source tool', () => {
    render(<SearchReferencesDisplay references={mockReferences} />);

    // 检查工具分组标题
    expect(screen.getByText('Tavily 网络搜索')).toBeInTheDocument();
    expect(screen.getByText('Arxiv 学术检索')).toBeInTheDocument();
    expect(screen.getByText('Bocha 搜索')).toBeInTheDocument();
  });

  test('should display correct result counts per tool', () => {
    render(<SearchReferencesDisplay references={mockReferences} />);

    // 每个工具都应该显示 "1 条结果"
    const resultCounts = screen.getAllByText(/1 条结果/);
    expect(resultCounts).toHaveLength(3);
  });

  test('should render reference titles and snippets', () => {
    render(<SearchReferencesDisplay references={mockReferences} />);

    expect(screen.getByText('Modern Interior Design Trends 2024')).toBeInTheDocument();
    expect(screen.getByText(/Latest trends in modern interior design/)).toBeInTheDocument();
    expect(screen.getByText('Architectural Psychology Research Paper')).toBeInTheDocument();
    expect(screen.getByText('办公空间设计案例')).toBeInTheDocument();
  });

  test('should render external links for references with URLs', () => {
    render(<SearchReferencesDisplay references={mockReferences} />);

    const links = screen.getAllByRole('link');
    expect(links.length).toBeGreaterThan(0);

    // 检查第一个链接
    expect(links[0]).toHaveAttribute('href', 'https://example.com/article1');
    expect(links[0]).toHaveAttribute('target', '_blank');
    expect(links[0]).toHaveAttribute('rel', 'noopener noreferrer');
  });

  test('should display relevance scores when available', () => {
    render(<SearchReferencesDisplay references={mockReferences} />);

    expect(screen.getByText(/相关性: 95%/)).toBeInTheDocument();
    expect(screen.getByText(/相关性: 88%/)).toBeInTheDocument();
    expect(screen.getByText(/相关性: 92%/)).toBeInTheDocument();
  });

  test('should display quality scores when available', () => {
    render(<SearchReferencesDisplay references={mockReferences} />);

    expect(screen.getByText(/质量: 85分/)).toBeInTheDocument();
  });

  test('should display search queries', () => {
    render(<SearchReferencesDisplay references={mockReferences} />);

    expect(screen.getByText(/查询: modern interior design trends/)).toBeInTheDocument();
    expect(screen.getByText(/查询: architectural psychology/)).toBeInTheDocument();
    expect(screen.getByText(/查询: 办公空间设计/)).toBeInTheDocument();
  });

  test('should apply custom className when provided', () => {
    const { container } = render(
      <SearchReferencesDisplay references={mockReferences} className="custom-class" />
    );

    const rootElement = container.firstChild as HTMLElement;
    expect(rootElement).toHaveClass('custom-class');
  });

  test('should handle references without quality_score gracefully', () => {
    const referencesWithoutQuality: SearchReference[] = [
      {
        source_tool: 'tavily',
        title: 'Test Reference',
        snippet: 'Test snippet',
        relevance_score: 0.9,
        deliverable_id: 'test-1',
        query: 'test query',
        timestamp: '2025-01-03T10:00:00Z'
      }
    ];

    render(<SearchReferencesDisplay references={referencesWithoutQuality} />);

    expect(screen.getByText('Test Reference')).toBeInTheDocument();
    // 质量分数不应该显示
    expect(screen.queryByText(/质量:/)).not.toBeInTheDocument();
  });

  test('should handle references without URL gracefully', () => {
    const referencesWithoutURL: SearchReference[] = [
      {
        source_tool: 'milvus',  // v7.154: ragflow → milvus
        title: 'Knowledge Base Entry',
        snippet: 'Internal knowledge base content',
        relevance_score: 0.85,
        deliverable_id: 'kb-1',
        query: 'knowledge search',
        timestamp: '2025-01-03T10:00:00Z'
      }
    ];

    render(<SearchReferencesDisplay references={referencesWithoutURL} />);

    expect(screen.getByText('Knowledge Base Entry')).toBeInTheDocument();
    // 应该没有外部链接
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  test('should render multiple references from same tool', () => {
    const multipleFromSameTool: SearchReference[] = [
      {
        source_tool: 'tavily',
        title: 'Article 1',
        snippet: 'First article',
        relevance_score: 0.9,
        deliverable_id: 'art-1',
        query: 'test',
        timestamp: '2025-01-03T10:00:00Z'
      },
      {
        source_tool: 'tavily',
        title: 'Article 2',
        snippet: 'Second article',
        relevance_score: 0.85,
        deliverable_id: 'art-2',
        query: 'test',
        timestamp: '2025-01-03T10:01:00Z'
      }
    ];

    render(<SearchReferencesDisplay references={multipleFromSameTool} />);

    expect(screen.getByText('Article 1')).toBeInTheDocument();
    expect(screen.getByText('Article 2')).toBeInTheDocument();
    expect(screen.getByText(/2 条结果/)).toBeInTheDocument();
  });
});
