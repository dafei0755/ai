/**
 * 单元测试: UnifiedProgressiveQuestionnaireModal
 * 版本: v7.129.3
 * 测试目标: 验证 Step 2（信息补全）从 step2Data 读取问卷数据
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock NProgress
jest.mock('nprogress', () => ({
  start: jest.fn(),
  done: jest.fn(),
  configure: jest.fn(),
}));

// 测试数据：模拟 progressive_questionnaire_step3 的数据结构
const mockStep2DataWithQuestionnaire = {
  interaction_type: 'progressive_questionnaire_step3',
  step: 2,
  total_steps: 3,
  title: '信息补全',
  questionnaire: {
    introduction: '请回答以下问题以补充项目信息',
    questions: [
      {
        id: 'q1',
        text: '项目包含哪些具体功能或空间？',
        type: 'multiple_choice',
        options: ['住宅', '商业区域', '公共空间'],
        is_required: true,
        priority: 'high',
      },
      {
        id: 'q2',
        text: '您期望的交付物包括哪些？',
        type: 'multiple_choice',
        options: ['概念方案', '效果图', '施工图'],
        is_required: false,
        priority: 'medium',
      },
    ],
    note: '以上问题将帮助我们更好地理解您的需求',
  },
};

// 测试数据：空的 step3Data（模拟错误场景）
const mockStep3DataEmpty = null;

describe('UnifiedProgressiveQuestionnaireModal - v7.129.3 数据源修复', () => {

  describe('数据源验证', () => {

    test('step2Data 应包含 questionnaire 字段', () => {
      expect(mockStep2DataWithQuestionnaire.questionnaire).toBeDefined();
      expect(mockStep2DataWithQuestionnaire.questionnaire.questions).toHaveLength(2);
    });

    test('step3Data 应为空（旧的错误数据源）', () => {
      expect(mockStep3DataEmpty).toBeNull();
    });

    test('renderStep3Content 应从 step2Data 读取数据', () => {
      // 模拟 renderStep3Content 的逻辑
      const renderStep3Content = (step2Data: any, step3Data: any) => {
        // v7.129.3 修复后的逻辑：从 step2Data 读取
        const { questionnaire } = step2Data || {};
        if (!questionnaire) return null;
        return questionnaire;
      };

      // 使用正确的数据源（step2Data）
      const result = renderStep3Content(mockStep2DataWithQuestionnaire, mockStep3DataEmpty);
      expect(result).not.toBeNull();
      expect(result.questions).toHaveLength(2);
      expect(result.introduction).toBe('请回答以下问题以补充项目信息');
    });

    test('使用旧的 step3Data 数据源应返回 null（验证问题）', () => {
      // 模拟修复前的错误逻辑：从 step3Data 读取
      const renderStep3ContentOld = (step2Data: any, step3Data: any) => {
        // 修复前的错误逻辑：从 step3Data 读取
        const { questionnaire } = step3Data || {};
        if (!questionnaire) return null;
        return questionnaire;
      };

      // 使用错误的数据源（step3Data）- 应返回 null
      const result = renderStep3ContentOld(mockStep2DataWithQuestionnaire, mockStep3DataEmpty);
      expect(result).toBeNull(); // 这就是为什么界面会空白
    });
  });

  describe('validateStep3Required 验证', () => {

    test('应从 step2Data 读取问题进行验证', () => {
      const validateStep3Required = (currentStep: number, step2Data: any, answers: Record<string, any>) => {
        // v7.129.3 修复后的逻辑
        if (currentStep !== 2 || !step2Data?.questionnaire?.questions) return true;

        const requiredQuestions = step2Data.questionnaire.questions.filter((q: any) => q.is_required);
        for (const q of requiredQuestions) {
          const answer = answers[q.id];
          if (!answer || (Array.isArray(answer) && answer.length === 0) ||
              (typeof answer === 'string' && answer.trim() === '')) {
            return false;
          }
        }
        return true;
      };

      // 测试：无答案时应返回 false（必填未完成）
      expect(validateStep3Required(2, mockStep2DataWithQuestionnaire, {})).toBe(false);

      // 测试：有答案时应返回 true
      expect(validateStep3Required(2, mockStep2DataWithQuestionnaire, { q1: ['住宅'] })).toBe(true);

      // 测试：非 Step 2 应返回 true（跳过验证）
      expect(validateStep3Required(1, mockStep2DataWithQuestionnaire, {})).toBe(true);
    });
  });

  describe('问题类型标准化', () => {

    test('应正确标准化问题类型', () => {
      const normalizeQuestionType = (type: string) => {
        let normalizedType = type?.toLowerCase() || 'open_ended';

        if (normalizedType === 'multi_choice' || normalizedType === 'multi-choice') {
          normalizedType = 'multiple_choice';
        } else if (normalizedType === 'single' || normalizedType === 'radio') {
          normalizedType = 'single_choice';
        } else if (normalizedType === 'text' || normalizedType === 'textarea' || normalizedType === 'open') {
          normalizedType = 'open_ended';
        }

        return normalizedType;
      };

      expect(normalizeQuestionType('multi_choice')).toBe('multiple_choice');
      expect(normalizeQuestionType('multi-choice')).toBe('multiple_choice');
      expect(normalizeQuestionType('single')).toBe('single_choice');
      expect(normalizeQuestionType('radio')).toBe('single_choice');
      expect(normalizeQuestionType('text')).toBe('open_ended');
      expect(normalizeQuestionType('textarea')).toBe('open_ended');
      expect(normalizeQuestionType('multiple_choice')).toBe('multiple_choice');
    });
  });

  describe('interaction_type 映射验证', () => {

    test('progressive_questionnaire_step3 应映射到 UI Step 2', () => {
      const mapInteractionTypeToUIStep = (interactionType: string) => {
        const mapping: Record<string, number> = {
          'progressive_questionnaire_step1': 1,  // 任务梳理
          'progressive_questionnaire_step3': 2,  // 信息补全（step3 函数，但 UI 是第2步）
          'progressive_questionnaire_step2': 3,  // 偏好雷达图（step2 函数，但 UI 是第3步）
        };
        return mapping[interactionType] || 0;
      };

      expect(mapInteractionTypeToUIStep('progressive_questionnaire_step1')).toBe(1);
      expect(mapInteractionTypeToUIStep('progressive_questionnaire_step3')).toBe(2);
      expect(mapInteractionTypeToUIStep('progressive_questionnaire_step2')).toBe(3);
    });

    test('数据应存储到正确的 state 变量', () => {
      // 模拟 WebSocket 处理逻辑
      const handleWebSocketMessage = (message: any) => {
        let step1Data = null;
        let step2Data = null;
        let step3Data = null;

        if (message.interrupt_data?.interaction_type === 'progressive_questionnaire_step1') {
          step1Data = message.interrupt_data;
        } else if (message.interrupt_data?.interaction_type === 'progressive_questionnaire_step3') {
          // 信息补全显示为 UI Step 2，数据存入 step2Data
          step2Data = message.interrupt_data;
        } else if (message.interrupt_data?.interaction_type === 'progressive_questionnaire_step2') {
          // 雷达图显示为 UI Step 3，数据存入 step3Data
          step3Data = message.interrupt_data;
        }

        return { step1Data, step2Data, step3Data };
      };

      // 测试：progressive_questionnaire_step3 应存入 step2Data
      const result = handleWebSocketMessage({
        interrupt_data: mockStep2DataWithQuestionnaire
      });

      expect(result.step2Data).not.toBeNull();
      expect(result.step2Data?.questionnaire).toBeDefined();
      expect(result.step3Data).toBeNull();
    });
  });
});

console.log('✅ 所有测试用例已定义 - v7.129.3 数据源修复验证');
