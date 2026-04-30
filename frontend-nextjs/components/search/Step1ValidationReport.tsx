import React, { useState } from 'react';

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

interface Step1ValidationReportProps {
  report: ValidationReport;
  onRegenerate?: () => void;
}

const Step1ValidationReport: React.FC<Step1ValidationReportProps> = ({
  report,
  onRegenerate
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Don't show if all checks passed
  if (report.overall_status === 'passed') {
    return null;
  }

  // Status indicator
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'passed':
        return '🟢';
      case 'warning':
        return '🟡';
      case 'failed':
        return '🔴';
      default:
        return '⚪';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'passed':
        return 'bg-green-50 border-green-200 text-green-800';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      case 'failed':
        return 'bg-red-50 border-red-200 text-red-800';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  const failedChecks = report.checks.filter(c => c.status === 'failed');
  const warningChecks = report.checks.filter(c => c.status === 'warning');

  return (
    <div className={`rounded-lg border-2 p-4 md:p-6 ${getStatusColor(report.overall_status)}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-start gap-3">
          <span className="text-3xl">{getStatusIcon(report.overall_status)}</span>
          <div>
            <h3 className="text-lg font-bold mb-1">
              {report.overall_status === 'failed' ? '分析质量检查未通过' : '分析质量警告'}
            </h3>
            <p className="text-sm opacity-90">
              {failedChecks.length > 0 && `${failedChecks.length} 个严重问题`}
              {failedChecks.length > 0 && warningChecks.length > 0 && '，'}
              {warningChecks.length > 0 && `${warningChecks.length} 个警告`}
            </p>
          </div>
        </div>

        {/* Regenerate Button */}
        {onRegenerate && (
          <button
            onClick={onRegenerate}
            className="px-4 py-2 bg-white border border-current rounded-lg hover:bg-opacity-90 transition-colors text-sm font-medium"
          >
            🔄 重新生成
          </button>
        )}
      </div>

      {/* Summary */}
      <div className="mb-4">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-sm font-medium hover:underline"
        >
          <span>{isExpanded ? '▼' : '▶'}</span>
          <span>{isExpanded ? '收起详情' : '查看详情'}</span>
        </button>
      </div>

      {/* Detailed Checks */}
      {isExpanded && (
        <div className="space-y-3 mt-4 pt-4 border-t border-current border-opacity-20">
          {report.checks.map((check, index) => (
            <div
              key={index}
              className="bg-white bg-opacity-50 rounded-lg p-3"
            >
              <div className="flex items-start gap-2">
                <span className="text-xl">{getStatusIcon(check.status)}</span>
                <div className="flex-1">
                  <div className="font-medium text-sm mb-1">{check.name}</div>
                  <div className="text-sm opacity-90">{check.message}</div>
                  {check.details && (
                    <div className="text-xs opacity-75 mt-2 p-2 bg-white bg-opacity-50 rounded">
                      {check.details}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Timestamp */}
      <div className="text-xs opacity-60 mt-4">
        验证时间: {new Date(report.timestamp).toLocaleString('zh-CN')}
      </div>
    </div>
  );
};

export default Step1ValidationReport;
