// app/report/[sessionId]/page.tsx
// 报告展示页面：提供报告阅读、下载及追问入口

'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { StructuredReport, FollowupTurn, FollowupAttachment } from '@/types';
import { Loader2, ArrowLeft, Download, MessageSquare, X, List, ArrowUp } from 'lucide-react';
import { WebSocketClient, WebSocketMessage } from '@/lib/websocket';
import {
  ExecutiveSummaryCard,
  ReportSectionCard,
  ExpertReportAccordion,
  ComprehensiveAnalysisCard,
  ConclusionsCard,
  ReviewVisualizationCard,
  TableOfContents,
  QuestionnaireSection,
  CoreAnswerSection,
  InsightsSection,
  DeliberationProcessSection,
  RecommendationsSection,
  ExecutionMetadataSection,
} from '@/components/report';
import RequirementsAnalysisSection from '@/components/report/RequirementsAnalysisSection';
import ChallengeDetectionCard from '@/components/report/ChallengeDetectionCard';
import { SearchReferencesDisplay } from '@/components/report/SearchReferencesDisplay';

const DEFAULT_FOLLOWUP_QUESTIONS = [
  '能否进一步分析关键技术的实现难点？',
  '请详细说明资源配置的优先级？',
  '有哪些潜在风险需要特别关注？',
  '能否提供更具体的实施时间表？'
];

interface ReportState {
  reportText: string;
  reportPdfPath?: string;
  createdAt?: string;
  userInput?: string;  // 用户原始输入
  structuredReport?: StructuredReport | null;
  analysisMode?: 'normal' | 'deep_thinking';  // 🆕 分析模式
}

// 🔥 v7.109: 使用全局类型定义（从 @/types 导入）
// interface FollowupTurn 已从 @/types 导入

type FetchStatus = 'idle' | 'loading' | 'success' | 'error';

export default function ReportPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [fetchStatus, setFetchStatus] = useState<FetchStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ReportState | null>(null);
  const [showToc, setShowToc] = useState<boolean>(true);

  const [showFollowupDialog, setShowFollowupDialog] = useState<boolean>(false);
  const [followupQuestion, setFollowupQuestion] = useState<string>('');
  const [followupSubmitting, setFollowupSubmitting] = useState<boolean>(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>(DEFAULT_FOLLOWUP_QUESTIONS);
  const [loadingSuggestions, setLoadingSuggestions] = useState<boolean>(false);
  const [suggestionHint, setSuggestionHint] = useState<string | null>(null);

  // 🔥 v3.11 新增：追问对话历史
  const [followupHistory, setFollowupHistory] = useState<FollowupTurn[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);

  // 🔥 v7.109: 返回顶部按钮状态
  const [showBackToTop, setShowBackToTop] = useState<boolean>(false);

  // 🔥 v7.108.2 新增：图片上传状态
  const [uploadedImage, setUploadedImage] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 🔥 v3.11 新增：WebSocket客户端引用
  const wsClientRef = useRef<WebSocketClient | null>(null);

  // 🔥 v3.11 新增：WebSocket连接 - 用于实时接收追问回答
  useEffect(() => {
    if (!showFollowupDialog) {
      // 对话框关闭时，断开WebSocket
      if (wsClientRef.current) {
        console.log('🔌 关闭WebSocket连接（追问对话框已关闭）');
        wsClientRef.current.close();
        wsClientRef.current = null;
      }
      return;
    }

    // 对话框打开时，建立WebSocket连接
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

    wsClientRef.current = new WebSocketClient({
      url: API_BASE_URL,
      sessionId: sessionId,
      onMessage: (message: WebSocketMessage) => {
        console.log('📨 收到WebSocket消息:', message);

        // 🔥 处理追问回答推送
        if (message.type === 'followup_answer') {
          console.log('✅ 收到追问回答:', message);

          // 更新历史记录（替换"正在生成回答..."的占位条目）
          setFollowupHistory(prev => {
            const updated = [...prev];
            const index = updated.findIndex(t => t.turn_id === message.turn_id);

            if (index !== -1) {
              // 更新现有条目
              updated[index] = {
                turn_id: message.turn_id,
                question: message.question,
                answer: message.answer,
                intent: message.intent,
                referenced_sections: message.referenced_sections || [],
                timestamp: message.timestamp
              };
            } else {
              // 添加新条目
              updated.push({
                turn_id: message.turn_id,
                question: message.question,
                answer: message.answer,
                intent: message.intent,
                referenced_sections: message.referenced_sections || [],
                timestamp: message.timestamp
              });
            }

            return updated;
          });
        }
      },
      onError: (error) => {
        console.error('❌ WebSocket错误:', error);
      },
      onClose: () => {
        console.log('🔌 WebSocket连接已关闭');
      }
    });

    wsClientRef.current.connect();
    console.log('🔌 已建立WebSocket连接（追问对话）');

    // 清理函数
    return () => {
      if (wsClientRef.current) {
        console.log('🔌 清理WebSocket连接');
        wsClientRef.current.close();
        wsClientRef.current = null;
      }
    };
  }, [showFollowupDialog, sessionId]);

  // 🔥 v7.109: 监听滚动 - 控制返回顶部按钮显示
  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY;
      const pageHeight = document.documentElement.scrollHeight - window.innerHeight;
      const scrollPercentage = scrollPosition / pageHeight;

      // 滚动超过三分之二时显示按钮
      setShowBackToTop(scrollPercentage > 0.66);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // 🔥 v7.109: 返回顶部处理函数
  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  };

  useEffect(() => {
    const fetchReport = async () => {
      setFetchStatus('loading');
      setError(null);
      try {
        const result = await api.getReport(sessionId);

        // 🔍 调试：检查关键数据是否存在
        console.log('📊 报告数据检查:', {
          hasQuestionnaireResponses: !!result.structured_report?.questionnaire_responses,
          hasRequirementsAnalysis: !!result.structured_report?.requirements_analysis,
          hasCoreAnswer: !!result.structured_report?.core_answer,
          questionnaireResponsesData: result.structured_report?.questionnaire_responses,
          requirementsAnalysisData: result.structured_report?.requirements_analysis,
          coreAnswerData: result.structured_report?.core_answer,
        });

        setReport({
          reportText: result.report_text,
          reportPdfPath: result.report_pdf_path,
          createdAt: result.created_at,
          userInput: result.user_input,  // 保存用户原始输入
          structuredReport: result.structured_report,
          analysisMode: result.analysis_mode,  // 🆕 保存分析模式
        });
        setFetchStatus('success');
      } catch (err: any) {
        console.error('获取分析报告失败:', err);
        if (err?.response?.status === 400) {
          // 报告尚未生成，引导回分析页面
          setError('报告尚未生成，正在回到分析流程...');
          setTimeout(() => {
            router.push(`/analysis/${sessionId}`);
          }, 1500);
        } else if (err?.response?.status === 404) {
          setError('会话不存在或已过期');
        } else {
          setError(err?.response?.data?.detail || '获取报告时发生错误');
        }
        setFetchStatus('error');
      }
    };

    fetchReport();
  }, [router, sessionId]);

  // 生成结构化 Markdown 格式的报告
  const generateStructuredMarkdown = (): string => {
    if (!report?.structuredReport) {
      return report?.reportText || '';
    }

    const sr = report.structuredReport;
    const lines: string[] = [];

    // 标题
    lines.push('# 项目分析报告');
    lines.push('');
    lines.push(`> 会话 ID: ${sessionId}`);
    lines.push(`> 生成时间: ${report.createdAt || new Date().toISOString()}`);
    if (sr.inquiry_architecture) {
      lines.push(`> 探询架构: ${sr.inquiry_architecture}`);
    }
    lines.push('');
    lines.push('---');
    lines.push('');

    // 用户原始需求
    if (report.userInput) {
      lines.push('## 用户原始需求');
      lines.push('');
      lines.push(report.userInput);
      lines.push('');
      lines.push('---');
      lines.push('');
    }

    // 执行摘要
    if (sr.executive_summary) {
      lines.push('## 执行摘要');
      lines.push('');
      if (sr.executive_summary.project_overview) {
        lines.push('### 项目概述');
        lines.push('');
        lines.push(sr.executive_summary.project_overview);
        lines.push('');
      }
      if (sr.executive_summary.key_findings?.length) {
        lines.push('### 关键发现');
        lines.push('');
        sr.executive_summary.key_findings.forEach(item => {
          lines.push(`- ${item}`);
        });
        lines.push('');
      }
      if (sr.executive_summary.key_recommendations?.length) {
        lines.push('### 核心建议');
        lines.push('');
        sr.executive_summary.key_recommendations.forEach(item => {
          lines.push(`- ${item}`);
        });
        lines.push('');
      }
      if (sr.executive_summary.success_factors?.length) {
        lines.push('### 成功要素');
        lines.push('');
        sr.executive_summary.success_factors.forEach(item => {
          lines.push(`- ${item}`);
        });
        lines.push('');
      }
    }

    // 详细分析章节
    if (sr.sections?.length) {
      lines.push('---');
      lines.push('');
      lines.push('## 详细分析');
      lines.push('');
      sr.sections.forEach(section => {
        lines.push(`### ${section.title}`);
        lines.push('');
        lines.push(section.content);
        if (section.confidence) {
          lines.push('');
          lines.push(`*置信度: ${(section.confidence * 100).toFixed(0)}%*`);
        }
        lines.push('');
      });
    }

    // 综合分析
    if (sr.comprehensive_analysis) {
      lines.push('---');
      lines.push('');
      lines.push('## 综合分析');
      lines.push('');
      const ca = sr.comprehensive_analysis;
      if (ca.cross_domain_insights?.length) {
        lines.push('### 跨领域洞察');
        lines.push('');
        ca.cross_domain_insights.forEach(item => {
          lines.push(`- ${item}`);
        });
        lines.push('');
      }
      if (ca.integrated_recommendations?.length) {
        lines.push('### 整合建议');
        lines.push('');
        ca.integrated_recommendations.forEach(item => {
          lines.push(`- ${item}`);
        });
        lines.push('');
      }
      if (ca.risk_assessment?.length) {
        lines.push('### 风险评估');
        lines.push('');
        ca.risk_assessment.forEach(item => {
          lines.push(`- ${item}`);
        });
        lines.push('');
      }
      if (ca.implementation_roadmap?.length) {
        lines.push('### 实施路线图');
        lines.push('');
        ca.implementation_roadmap.forEach(item => {
          lines.push(`- ${item}`);
        });
        lines.push('');
      }
    }

    // 结论与建议
    if (sr.conclusions) {
      lines.push('---');
      lines.push('');
      lines.push('## 结论与建议');
      lines.push('');
      if (sr.conclusions.project_analysis_summary) {
        lines.push('### 分析总结');
        lines.push('');
        lines.push(sr.conclusions.project_analysis_summary);
        lines.push('');
      }
      if (sr.conclusions.next_steps?.length) {
        lines.push('### 下一步行动');
        lines.push('');
        sr.conclusions.next_steps.forEach((item, i) => {
          lines.push(`${i + 1}. ${item}`);
        });
        lines.push('');
      }
      if (sr.conclusions.success_metrics?.length) {
        lines.push('### 成功指标');
        lines.push('');
        sr.conclusions.success_metrics.forEach(item => {
          lines.push(`- ${item}`);
        });
        lines.push('');
      }
    }

    lines.push('---');
    lines.push('');
    lines.push('*本报告由 设计高参 · 智能项目分析系统 自动生成*');

    return lines.join('\n');
  };

  // 生成打印用的 HTML 内容
  const generatePrintHTML = (): string => {
    if (!report?.structuredReport) {
      return `<pre>${report?.reportText || ''}</pre>`;
    }

    const sr = report.structuredReport;
    const sections: string[] = [];

    // CSS 样式
    const styles = `
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans SC", sans-serif;
          line-height: 1.8;
          color: #333;
          padding: 40px;
          max-width: 800px;
          margin: 0 auto;
        }
        h1 { font-size: 28px; margin-bottom: 20px; color: #1a1a1a; border-bottom: 3px solid #3b82f6; padding-bottom: 10px; }
        h2 { font-size: 22px; margin: 30px 0 15px; color: #1a1a1a; border-left: 4px solid #3b82f6; padding-left: 12px; }
        h3 { font-size: 18px; margin: 20px 0 10px; color: #374151; }
        p { margin: 10px 0; text-align: justify; }
        ul, ol { margin: 10px 0 10px 20px; }
        li { margin: 6px 0; }
        .meta { color: #6b7280; font-size: 14px; margin-bottom: 20px; }
        .meta span { display: block; margin: 4px 0; }
        .user-input { background: #f3f4f6; padding: 15px 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3b82f6; }
        .section { margin: 25px 0; page-break-inside: avoid; }
        .divider { border-top: 1px solid #e5e7eb; margin: 30px 0; }
        .footer { text-align: left; color: #666; font-size: 11px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; }
        .confidence { color: #6b7280; font-size: 13px; font-style: italic; }
        /* 打印页眉页脚遮罩 */
        .print-header-cover {
          display: none;
        }
        .print-footer-cover {
          display: none;
        }
        @media print {
          body { padding: 0; margin: 0; }
          .section { page-break-inside: avoid; }
          /* 顶部遮罩层 - 覆盖浏览器默认页眉 */
          .print-header-cover {
            display: block;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 20mm;
            background: white;
            z-index: 9999;
          }
          /* 底部遮罩层 + 自定义页脚 */
          .print-footer-cover {
            display: block;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: 15mm;
            background: white;
            z-index: 9999;
            padding: 3mm 15mm;
            font-size: 10px;
            color: #666;
          }
          @page {
            margin: 20mm 15mm 15mm 15mm;
            size: A4;
          }
        }
      </style>
    `;

    // 标题和元信息
    sections.push(`
      <h1>项目分析报告</h1>
      <div class="meta">
        <span>会话 ID: ${sessionId}</span>
        <span>生成时间: ${report.createdAt || new Date().toLocaleString('zh-CN')}</span>
        ${sr.inquiry_architecture ? `<span>探询架构: ${sr.inquiry_architecture}</span>` : ''}
      </div>
    `);

    // 用户原始需求
    if (report.userInput) {
      sections.push(`
        <div class="section">
          <h2>用户原始需求</h2>
          <div class="user-input">${report.userInput}</div>
        </div>
        <div class="divider"></div>
      `);
    }

    // 执行摘要
    if (sr.executive_summary) {
      let summaryHTML = '<div class="section"><h2>执行摘要</h2>';

      if (sr.executive_summary.project_overview) {
        summaryHTML += `<h3>项目概述</h3><p>${sr.executive_summary.project_overview}</p>`;
      }
      if (sr.executive_summary.key_findings?.length) {
        summaryHTML += '<h3>关键发现</h3><ul>';
        sr.executive_summary.key_findings.forEach(item => {
          summaryHTML += `<li>${item}</li>`;
        });
        summaryHTML += '</ul>';
      }
      if (sr.executive_summary.key_recommendations?.length) {
        summaryHTML += '<h3>核心建议</h3><ul>';
        sr.executive_summary.key_recommendations.forEach(item => {
          summaryHTML += `<li>${item}</li>`;
        });
        summaryHTML += '</ul>';
      }
      if (sr.executive_summary.success_factors?.length) {
        summaryHTML += '<h3>成功要素</h3><ul>';
        sr.executive_summary.success_factors.forEach(item => {
          summaryHTML += `<li>${item}</li>`;
        });
        summaryHTML += '</ul>';
      }

      summaryHTML += '</div><div class="divider"></div>';
      sections.push(summaryHTML);
    }

    // 详细分析章节
    if (sr.sections?.length) {
      let sectionsHTML = '<div class="section"><h2>详细分析</h2>';
      sr.sections.forEach(section => {
        sectionsHTML += `<h3>${section.title}</h3><p>${section.content.replace(/\n/g, '</p><p>')}</p>`;
        if (section.confidence) {
          sectionsHTML += `<p class="confidence">置信度: ${(section.confidence * 100).toFixed(0)}%</p>`;
        }
      });
      sectionsHTML += '</div><div class="divider"></div>';
      sections.push(sectionsHTML);
    }

    // 综合分析
    if (sr.comprehensive_analysis) {
      let caHTML = '<div class="section"><h2>综合分析</h2>';
      const ca = sr.comprehensive_analysis;

      if (ca.cross_domain_insights?.length) {
        caHTML += '<h3>跨领域洞察</h3><ul>';
        ca.cross_domain_insights.forEach(item => { caHTML += `<li>${item}</li>`; });
        caHTML += '</ul>';
      }
      if (ca.integrated_recommendations?.length) {
        caHTML += '<h3>整合建议</h3><ul>';
        ca.integrated_recommendations.forEach(item => { caHTML += `<li>${item}</li>`; });
        caHTML += '</ul>';
      }
      if (ca.risk_assessment?.length) {
        caHTML += '<h3>风险评估</h3><ul>';
        ca.risk_assessment.forEach(item => { caHTML += `<li>${item}</li>`; });
        caHTML += '</ul>';
      }
      if (ca.implementation_roadmap?.length) {
        caHTML += '<h3>实施路线图</h3><ul>';
        ca.implementation_roadmap.forEach(item => { caHTML += `<li>${item}</li>`; });
        caHTML += '</ul>';
      }

      caHTML += '</div><div class="divider"></div>';
      sections.push(caHTML);
    }

    // 结论与建议
    if (sr.conclusions) {
      let concHTML = '<div class="section"><h2>结论与建议</h2>';

      if (sr.conclusions.project_analysis_summary) {
        concHTML += `<h3>分析总结</h3><p>${sr.conclusions.project_analysis_summary}</p>`;
      }
      if (sr.conclusions.next_steps?.length) {
        concHTML += '<h3>下一步行动</h3><ol>';
        sr.conclusions.next_steps.forEach(item => { concHTML += `<li>${item}</li>`; });
        concHTML += '</ol>';
      }
      if (sr.conclusions.success_metrics?.length) {
        concHTML += '<h3>成功指标</h3><ul>';
        sr.conclusions.success_metrics.forEach(item => { concHTML += `<li>${item}</li>`; });
        concHTML += '</ul>';
      }

      concHTML += '</div>';
      sections.push(concHTML);
    }

    // 页脚已改用固定定位，不再需要此处
    // sections.push('<div class="footer">极致概念@方案高参</div>');

    return `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>项目分析报告</title>${styles}</head><body>
      <div class="print-header-cover"></div>
      <div class="print-footer-cover">极致概念@方案高参</div>
      ${sections.join('')}</body></html>`;
  };

  // 下载 PDF 报告（通过后端 API 生成）
  const handleDownloadReport = async () => {
    if (!report) return;

    try {
      // 调用后端 API 下载 PDF
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/analysis/report/${sessionId}/download-pdf`);

      if (!response.ok) {
        throw new Error('下载失败');
      }

      // 获取 PDF 数据
      const blob = await response.blob();

      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `项目分析报告_${sessionId}.pdf`;
      document.body.appendChild(a);
      a.click();

      // 清理
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('下载 PDF 失败:', error);
      alert('下载失败，请稍后重试');
    }
  };

  const handleOpenFollowup = async () => {
    setShowFollowupDialog(true);
    setSuggestionHint(null);

    // 🔥 v3.11: 加载追问历史
    setLoadingHistory(true);
    try {
      const historyResult = await api.getFollowupHistory(sessionId);
      setFollowupHistory(historyResult.history || []);
      console.log('✅ 已加载追问历史:', historyResult.total_turns, '轮');
    } catch (err) {
      console.error('⚠️ 加载追问历史失败:', err);
      // 不阻断流程，继续显示对话框
      setFollowupHistory([]);
    } finally {
      setLoadingHistory(false);
    }

    // 🔥 打开对话框时异步加载智能推荐问题
    setLoadingSuggestions(true);
    try {
      const result = await api.generateFollowupQuestions(sessionId);
      if (result.questions && result.questions.length > 0) {
        setSuggestedQuestions(result.questions);
        console.log('✅ 已加载智能推荐问题:', result.questions);
      } else {
        setSuggestedQuestions(DEFAULT_FOLLOWUP_QUESTIONS);
      }

      if (result.source === 'fallback') {
        setSuggestionHint(result.message || '智能推荐暂不可用，已为您提供通用问题，可直接输入自定义追问。');
      } else {
        setSuggestionHint(null);
      }
    } catch (err) {
      console.error('⚠️ 加载推荐问题失败，使用默认问题:', err);
      // 🔥 新增：显示用户友好的提示（非阻断式）
      console.warn('💡 提示：智能推荐问题生成失败，已为您提供通用问题建议。您也可以直接输入自己的问题。');
      // 保持默认问题，不弹出alert以免打断用户
      setSuggestedQuestions(DEFAULT_FOLLOWUP_QUESTIONS);
      setSuggestionHint('智能推荐问题生成失败，已展示通用问题，您也可以直接输入自己的追问。');
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const handleCloseFollowup = () => {
    setShowFollowupDialog(false);
    setFollowupQuestion('');
    setSuggestionHint(null);
  };

  // 🔥 v7.108.2 新增：图片上传处理
  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      alert('请上传图片文件');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      alert('图片过大（最大10MB）');
      return;
    }

    setUploadedImage(file);
    const reader = new FileReader();
    reader.onload = (e) => setImagePreviewUrl(e.target?.result as string);
    reader.readAsDataURL(file);
  };

  const handleFollowupSubmit = async () => {
    if (!followupQuestion.trim()) {
      alert('请输入您的问题');
      return;
    }

    try {
      setFollowupSubmitting(true);

      // 🔥 v7.108.2：支持图片上传
      const result = await api.submitFollowupQuestion(
        sessionId,
        followupQuestion.trim(),
        uploadedImage || undefined
      );

      console.log('✅ 追问提交成功，会话ID:', result.session_id);

      const tempTurn: FollowupTurn = {
        turn_id: followupHistory.length + 1,
        question: followupQuestion.trim(),
        answer: '正在生成回答...',
        intent: 'general',
        referenced_sections: [],
        attachments: uploadedImage ? [{
          type: 'image',
          original_filename: uploadedImage.name,
          url: imagePreviewUrl || '',
          thumbnail_url: imagePreviewUrl || '',
          width: 0,
          height: 0,
          format: uploadedImage.type
        }] : undefined,
        timestamp: new Date().toISOString()
      };
      setFollowupHistory(prev => [...prev, tempTurn]);

      // 清空输入框和图片
      setFollowupQuestion('');
      setUploadedImage(null);
      setImagePreviewUrl(null);

      console.log('💡 等待WebSocket推送回答...');
    } catch (err: any) {
      console.error('追问提交失败:', err);
      console.error('错误详情:', err?.response?.data || err.message);

      const errorMessage = err?.response?.data?.detail || err.message || '追问提交失败，请稍后再试';
      alert(`追问提交失败: ${errorMessage}`);
    } finally {
      setFollowupSubmitting(false);
    }
  };

  const renderContent = () => {
    if (fetchStatus === 'loading') {
      return (
        <div className="flex flex-col items-center justify-center h-96 text-gray-400 gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-[var(--primary)]" />
          <p>正在加载分析报告...</p>
        </div>
      );
    }

    if (fetchStatus === 'error') {
      return (
        <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-8 text-center text-red-300">
          <p className="text-lg font-semibold mb-2">无法加载报告</p>
          <p className="text-sm mb-4">{error || '请稍后再试'}</p>
          <button
            onClick={() => router.push(`/analysis/${sessionId}`)}
            className="px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white rounded-lg transition-colors"
          >
            返回分析流程
          </button>
        </div>
      );
    }

    if (!report?.reportText) {
      return (
        <div className="flex flex-col items-center justify-center h-96 text-gray-400 gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-[var(--primary)]" />
          <p>报告生成中，请稍候...</p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {/* 报告头部 */}
        <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-white">分析报告</h1>
            <p className="text-sm text-gray-400 mt-2">
              会话 ID：{sessionId}
              {report.createdAt ? ` · 生成时间：${new Date(report.createdAt).toLocaleString('zh-CN')}` : ''}
              {report.structuredReport?.inquiry_architecture && (
                <span className="ml-2 px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs">
                  {report.structuredReport.inquiry_architecture}
                </span>
              )}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleDownloadReport}
              className="px-4 py-2.5 bg-[var(--sidebar-bg)] hover:bg-gray-700 text-white rounded-lg transition-colors border border-[var(--border-color)] flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              下载报告
            </button>
            <button
              onClick={handleOpenFollowup}
              className="px-4 py-2.5 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white rounded-lg transition-colors flex items-center gap-2"
            >
              <MessageSquare className="w-4 h-4" />
              后续追问
            </button>
          </div>
        </div>

        {/* 结构化视图 */}
        {report.structuredReport ? (
          <div className="flex gap-6">
            {/* 侧边导航 */}
            {showToc && (
              <div className="hidden lg:block sticky top-6 self-start">
                <TableOfContents report={report.structuredReport} />
              </div>
            )}

            {/* 主内容区域 - 🔥 Phase 1.4+ 重构：新的报告结构 */}
            <div className="flex-1 space-y-6">
              {/* 1. 用户原始需求 */}
              {report.userInput && (
                <div id="user-question" className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-xl p-6">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                      <MessageSquare className="w-5 h-5 text-blue-400" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-blue-400 mb-2">用户原始需求</h3>
                      <p className="text-gray-200 whitespace-pre-wrap leading-relaxed">{report.userInput}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* 2. 校准问卷（只呈现有采纳的部分内容） */}
              <QuestionnaireSection questionnaireData={report.structuredReport.questionnaire_responses} />

              {/* 3. 需求分析结果（需求分析师原始输出） */}
              {report.structuredReport.requirements_analysis && (
                <RequirementsAnalysisSection requirements={report.structuredReport.requirements_analysis} />
              )}

              {/* 4. 需求洞察（LLM综合洞察） - 已取消展示 */}
              {/* <InsightsSection insights={report.structuredReport.insights} /> */}

              {/* 5. 答案（核心答案TL;DR） */}
              <CoreAnswerSection coreAnswer={report.structuredReport.core_answer} />

              {/* 6. 专家报告（可下载） */}
              {report.structuredReport.expert_reports && Object.keys(report.structuredReport.expert_reports).length > 0 && (
                <div id="expert-reports">
                  <ExpertReportAccordion
                    expertReports={report.structuredReport.expert_reports}
                    userInput={report.userInput}
                    sessionId={sessionId}
                    generatedImagesByExpert={report.structuredReport.generated_images_by_expert}
                  />
                </div>
              )}

              {/* 🆕 v7.120: 搜索引用 */}
              {report.structuredReport.search_references &&
               report.structuredReport.search_references.length > 0 && (
                <div id="search-references">
                  <SearchReferencesDisplay
                    references={report.structuredReport.search_references}
                  />
                </div>
              )}

              {/* 7. 推敲过程 */}
              <DeliberationProcessSection deliberationProcess={report.structuredReport.deliberation_process} />

              {/* 8. 建议提醒 */}
              <RecommendationsSection recommendations={report.structuredReport.recommendations} />

              {/* 9. 执行元数据汇总 */}
              <ExecutionMetadataSection
                metadata={report.structuredReport.execution_metadata}
                expertReportsCount={Object.keys(report.structuredReport.expert_reports || {}).length}
              />

              {/* 旧版数据区块已移除 - v7.0 简化报告结构 */}
            </div>
          </div>
        ) : (
          /* 原始文本视图 */
          <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-6">
            <div className="bg-[var(--sidebar-bg)] rounded-lg p-6 border border-[var(--border-color)] whitespace-pre-wrap font-mono text-sm text-gray-200 max-h-[70vh] overflow-y-auto">
              {report.reportText}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      {/* v7.290.1: 顶部导航栏 - 统一体验 */}
      <header className="sticky top-0 z-10 bg-[var(--sidebar-bg)] border-b border-[var(--border-color)]">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push('/')}
              className="p-2 text-[var(--foreground-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--card-bg)] rounded-lg transition-colors"
              title="返回首页"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-lg font-semibold">分析报告查看</h1>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-10">
        {renderContent()}
      </main>

      {/* 🔥 v3.11 改造：ChatGPT风格的连续对话界面 */}
      {showFollowupDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-[var(--card-bg)] rounded-2xl border border-[var(--border-color)] shadow-2xl w-full max-w-4xl h-[85vh] flex flex-col">
            {/* 对话头部 */}
            <div className="p-6 border-b border-[var(--border-color)] flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-900/20 rounded-lg flex items-center justify-center">
                  <MessageSquare className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold">连续追问对话</h2>
                  <p className="text-sm text-gray-400 mt-1">
                    {followupHistory.length > 0
                      ? `已对话 ${followupHistory.length} 轮`
                      : '基于分析报告的深度对话'}
                  </p>
                </div>
              </div>
              <button
                onClick={handleCloseFollowup}
                className="p-2 text-gray-400 hover:text-white hover:bg-[var(--sidebar-bg)] rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* 对话历史区域（可滚动） */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {loadingHistory ? (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  <span>正在加载对话历史...</span>
                </div>
              ) : followupHistory.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-4">
                  <MessageSquare className="w-16 h-16 text-gray-600" />
                  <p className="text-lg">尚无对话历史</p>
                  <p className="text-sm text-gray-500">从下方推荐问题开始，或输入您的问题</p>
                </div>
              ) : (
                followupHistory.map((turn) => (
                  <div key={turn.turn_id} className="space-y-3">
                    {/* 用户问题 */}
                    <div className="flex justify-end">
                      <div className="max-w-[80%] bg-blue-600/20 border border-blue-600/30 rounded-2xl rounded-tr-sm px-4 py-3">
                        <p className="text-sm text-gray-300">{turn.question}</p>

                        {/* 🔥 v7.108.2: 显示图片缩略图 */}
                        {turn.attachments?.map((att, idx) => (
                          att.type === 'image' && (
                            <img
                              key={idx}
                              src={att.thumbnail_url}
                              alt={att.original_filename}
                              onClick={() => window.open(att.url, '_blank')}
                              className="cursor-pointer rounded border border-blue-500 hover:border-white h-32 mt-2 transition-all"
                              title={`点击查看原图 - ${att.original_filename}`}
                            />
                          )
                        ))}

                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(turn.timestamp).toLocaleString('zh-CN', {
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </p>
                      </div>
                    </div>

                    {/* 系统回答 */}
                    <div className="flex justify-start">
                      <div className="max-w-[85%] bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-2xl rounded-tl-sm px-4 py-3">
                        {turn.answer === '正在生成回答...' ? (
                          <div className="flex items-center gap-2 text-gray-400">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span className="text-sm">{turn.answer}</span>
                          </div>
                        ) : (
                          <>
                            <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
                              {turn.answer}
                            </p>
                            {turn.referenced_sections && turn.referenced_sections.length > 0 && (
                              <div className="mt-2 pt-2 border-t border-gray-700">
                                <p className="text-xs text-gray-500">
                                  📖 引用章节: {turn.referenced_sections.join(', ')}
                                </p>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* 输入区域 */}
            <div className="border-t border-[var(--border-color)] p-4 space-y-4 flex-shrink-0">
              {/* 智能推荐问题 */}
              {!loadingHistory && followupHistory.length === 0 && (
                <div>
                  <label className="text-xs text-gray-400 mb-2 block">
                    💡 智能推荐问题
                    {loadingSuggestions && <span className="ml-2 text-blue-400">正在生成...</span>}
                  </label>
                  {suggestionHint && !loadingSuggestions && (
                    <p className="text-xs text-amber-300 mb-2">{suggestionHint}</p>
                  )}
                  <div className="grid grid-cols-2 gap-2">
                    {loadingSuggestions ? (
                      Array.from({ length: 4 }).map((_, index) => (
                        <div
                          key={index}
                          className="px-3 py-2 bg-[var(--sidebar-bg)] rounded-lg border border-[var(--border-color)] animate-pulse"
                        >
                          <div className="h-3 bg-gray-700 rounded w-3/4"></div>
                        </div>
                      ))
                    ) : (
                      suggestedQuestions.map((suggestion, index) => (
                        <button
                          key={index}
                          onClick={() => setFollowupQuestion(suggestion)}
                          className="text-left px-3 py-2 bg-[var(--sidebar-bg)] hover:bg-gray-700 rounded-lg text-xs text-gray-300 transition-colors border border-[var(--border-color)] truncate"
                          title={suggestion}
                        >
                          {suggestion}
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}

              {/* 输入框 */}
              <div className="space-y-2">
                {/* 🔥 v7.108.2: 图片预览 */}
                {imagePreviewUrl && (
                  <div className="relative inline-block">
                    <img
                      src={imagePreviewUrl}
                      alt="预览"
                      className="h-20 rounded border border-blue-500"
                    />
                    <button
                      onClick={() => {
                        setUploadedImage(null);
                        setImagePreviewUrl(null);
                      }}
                      className="absolute -top-2 -right-2 bg-red-500 hover:bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm transition-colors"
                      title="删除图片"
                    >
                      ×
                    </button>
                  </div>
                )}

                <div className="flex gap-2">
                  {/* 🔥 v7.108.2: 隐藏的文件输入 */}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleImageSelect}
                    className="hidden"
                  />

                  {/* 🔥 v7.108.2: 上传按钮 */}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors flex items-center gap-2"
                    title="上传图片"
                  >
                    <span className="text-lg">📷</span>
                  </button>

                  <textarea
                    value={followupQuestion}
                    onChange={(e) => setFollowupQuestion(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleFollowupSubmit();
                      }
                    }}
                    placeholder="输入您的问题...（可上传图片，Shift+Enter换行，Enter发送）"
                    className="flex-1 px-4 py-3 bg-[var(--sidebar-bg)] border border-[var(--border-color)] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[var(--primary)] resize-none"
                    rows={2}
                  />
                  <button
                    onClick={handleFollowupSubmit}
                    disabled={followupSubmitting || !followupQuestion.trim()}
                    className="px-6 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  >
                    {followupSubmitting ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <MessageSquare className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>

              <p className="text-xs text-gray-500 text-center">
                💡 提示：对话历史将自动保存，下次打开时可继续查看
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 🔥 v7.109: 返回顶部按钮 */}
      <button
        onClick={scrollToTop}
        className={`
          fixed bottom-8 right-8 z-50
          w-12 h-12 rounded-full
          bg-gradient-to-br from-blue-500 to-purple-600
          hover:from-blue-600 hover:to-purple-700
          shadow-lg hover:shadow-xl
          flex items-center justify-center
          transition-all duration-300 ease-in-out
          ${showBackToTop
            ? 'opacity-100 translate-y-0'
            : 'opacity-0 translate-y-4 pointer-events-none'}
        `}
        aria-label="返回顶部"
      >
        <ArrowUp className="w-6 h-6 text-white" />
      </button>
    </div>
  );
}
