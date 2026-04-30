/**
 * 集成测试：applyInterruptDispatch 路由逻辑
 *
 * 策略：将 applyInterruptDispatch 的逻辑提取为可测函数，
 * 然后验证每种 interaction_type 调用了正确的 setter。
 * 通过 spy/mock 隔离外部依赖（api.resumeAnalysis）。
 */
export {};

// ── 类型定义（与 page.tsx 对齐）────────────────────────────────────────────

type InterruptSetters = {
  setQuestionnaireData: jest.Mock;
  setShowQuestionnaire: jest.Mock;
  setCurrentProgressiveStep: jest.Mock;
  setProgressiveStepData: jest.Mock;
  setRoleTaskReviewData: jest.Mock;
  setShowRoleTaskReview: jest.Mock;
  setUserQuestionData: jest.Mock;
  setShowUserQuestion: jest.Mock;
  setQualityPreflightData: jest.Mock;
  setShowQualityPreflight: jest.Mock;
  // 🔄 v10.2 Path B: setOutputIntentData / setShowOutputIntentModal 已移除
  setConfirmationData: jest.Mock;
  setShowConfirmation: jest.Mock;
  resumeAnalysis: jest.Mock;
};

/** 镜像 page.tsx 中 applyInterruptDispatch 的纯路由逻辑，与 React 解耦 */
function createApplyInterruptDispatch(setters: InterruptSetters, sessionId: string) {
  return function applyInterruptDispatch(interruptData: any) {
    if (!interruptData) return;
    const type = interruptData.interaction_type;
    if (type === 'calibration_questionnaire') {
      setters.setQuestionnaireData(interruptData.questionnaire);
      setters.setShowQuestionnaire(true);
    } else if (type === 'role_and_task_unified_review') {
      if (interruptData.close_previous_modal) {
        setters.setCurrentProgressiveStep(0);
        setters.setProgressiveStepData(null);
      }
      setters.setRoleTaskReviewData(interruptData);
      setters.setShowRoleTaskReview(true);
    } else if (type === 'user_question') {
      setters.setUserQuestionData(interruptData);
      setters.setShowUserQuestion(true);
    } else if (type === 'batch_confirmation') {
      setters.resumeAnalysis(sessionId, 'approve').catch(() => {});
    } else if (type === 'progressive_questionnaire_step1') {
      setters.setProgressiveStepData(interruptData);
      setters.setCurrentProgressiveStep(1);
    } else if (type === 'progressive_questionnaire_step2') {
      setters.setProgressiveStepData(interruptData);
      setters.setCurrentProgressiveStep(2);
    } else if (type === 'progressive_questionnaire_step3') {
      setters.setProgressiveStepData(interruptData);
      setters.setCurrentProgressiveStep(3);
    } else if (type === 'progressive_questionnaire_step4' || type === 'requirements_insight') {
      setters.setProgressiveStepData(interruptData);
      setters.setCurrentProgressiveStep(4);
    } else if (type === 'quality_preflight_warning') {
      setters.setQualityPreflightData(interruptData);
      setters.setShowQualityPreflight(true);
    } else if (type === 'output_intent_confirmation') {
      // 🔄 v10.2 Path B: 后端不再发送此 interrupt，兜底走通用确认框
      setters.setConfirmationData(interruptData);
      setters.setShowConfirmation(true);
    } else {
      setters.setConfirmationData(interruptData);
      setters.setShowConfirmation(true);
    }
  };
}

// ── 辅助 ──────────────────────────────────────────────────────────────────

function makeSetters(): InterruptSetters {
  return {
    setQuestionnaireData:    jest.fn(),
    setShowQuestionnaire:    jest.fn(),
    setCurrentProgressiveStep: jest.fn(),
    setProgressiveStepData:  jest.fn(),
    setRoleTaskReviewData:   jest.fn(),
    setShowRoleTaskReview:   jest.fn(),
    setUserQuestionData:     jest.fn(),
    setShowUserQuestion:     jest.fn(),
    setQualityPreflightData: jest.fn(),
    setShowQualityPreflight: jest.fn(),
    setConfirmationData:     jest.fn(),
    setShowConfirmation:     jest.fn(),
    resumeAnalysis:          jest.fn().mockResolvedValue(undefined),
  };
}

const SESSION_ID = 'test-session-001';

// ── 测试套件 ──────────────────────────────────────────────────────────────

describe('集成测试 > applyInterruptDispatch 路由逻辑', () => {
  let setters: InterruptSetters;
  let dispatch: ReturnType<typeof createApplyInterruptDispatch>;

  beforeEach(() => {
    setters = makeSetters();
    dispatch = createApplyInterruptDispatch(setters, SESSION_ID);
  });

  // ── guard ──
  it('interruptData 为 null 时直接返回，不触发任何 setter', () => {
    dispatch(null);
    dispatch(undefined);
    Object.values(setters).forEach((fn) => expect(fn).not.toHaveBeenCalled());
  });

  // ── calibration_questionnaire ──
  it('calibration_questionnaire → setShowQuestionnaire(true) + setQuestionnaireData', () => {
    const data = { interaction_type: 'calibration_questionnaire', questionnaire: { q: 1 } };
    dispatch(data);
    expect(setters.setQuestionnaireData).toHaveBeenCalledWith({ q: 1 });
    expect(setters.setShowQuestionnaire).toHaveBeenCalledWith(true);
    expect(setters.setShowRoleTaskReview).not.toHaveBeenCalled();
  });

  // ── role_and_task_unified_review ──
  it('role_and_task_unified_review → setShowRoleTaskReview(true)', () => {
    const data = { interaction_type: 'role_and_task_unified_review' };
    dispatch(data);
    expect(setters.setRoleTaskReviewData).toHaveBeenCalledWith(data);
    expect(setters.setShowRoleTaskReview).toHaveBeenCalledWith(true);
  });

  it('role_and_task_unified_review with close_previous_modal → 先关闭进度步骤', () => {
    dispatch({ interaction_type: 'role_and_task_unified_review', close_previous_modal: true });
    expect(setters.setCurrentProgressiveStep).toHaveBeenCalledWith(0);
    expect(setters.setProgressiveStepData).toHaveBeenCalledWith(null);
    expect(setters.setShowRoleTaskReview).toHaveBeenCalledWith(true);
  });

  // ── user_question ──
  it('user_question → setShowUserQuestion(true)', () => {
    const data = { interaction_type: 'user_question', text: '是否继续？' };
    dispatch(data);
    expect(setters.setUserQuestionData).toHaveBeenCalledWith(data);
    expect(setters.setShowUserQuestion).toHaveBeenCalledWith(true);
  });

  // ── batch_confirmation ──
  it('batch_confirmation → 自动调用 resumeAnalysis(approve)', () => {
    dispatch({ interaction_type: 'batch_confirmation' });
    expect(setters.resumeAnalysis).toHaveBeenCalledWith(SESSION_ID, 'approve');
    // 不应打开任何 modal
    expect(setters.setShowQuestionnaire).not.toHaveBeenCalled();
    expect(setters.setShowConfirmation).not.toHaveBeenCalled();
  });

  // ── progressive steps ──
  it.each([
    ['progressive_questionnaire_step1', 1],
    ['progressive_questionnaire_step2', 2],
    ['progressive_questionnaire_step3', 3],
    ['progressive_questionnaire_step4', 4],
  ])('%s → setCurrentProgressiveStep(%i)', (type, step) => {
    const data = { interaction_type: type, stages: [] };
    dispatch(data);
    expect(setters.setProgressiveStepData).toHaveBeenCalledWith(data);
    expect(setters.setCurrentProgressiveStep).toHaveBeenCalledWith(step);
  });

  it('requirements_insight → setCurrentProgressiveStep(4)（等效 step4）', () => {
    const data = { interaction_type: 'requirements_insight' };
    dispatch(data);
    expect(setters.setCurrentProgressiveStep).toHaveBeenCalledWith(4);
  });

  // ── quality_preflight_warning ──
  it('quality_preflight_warning → setShowQualityPreflight(true)', () => {
    const data = { interaction_type: 'quality_preflight_warning', warnings: [] };
    dispatch(data);
    expect(setters.setQualityPreflightData).toHaveBeenCalledWith(data);
    expect(setters.setShowQualityPreflight).toHaveBeenCalledWith(true);
  });

  // ── output_intent_confirmation（🔄 v10.2 Path B: 兜底走通用确认框）──
  it('output_intent_confirmation → setShowConfirmation(true)（Path B 兜底）', () => {
    const data = {
      interaction_type: 'output_intent_confirmation',
      delivery_types: { options: [], max_select: 3 },
      identity_modes: { options: [] },
    };
    dispatch(data);
    expect(setters.setConfirmationData).toHaveBeenCalledWith(data);
    expect(setters.setShowConfirmation).toHaveBeenCalledWith(true);
    expect(setters.setShowQuestionnaire).not.toHaveBeenCalled();
  });

  // ── 未知类型兜底 ──
  it('未知 interaction_type → setShowConfirmation(true)（兜底）', () => {
    const data = { interaction_type: 'future_unknown_type', msg: 'hello' };
    dispatch(data);
    expect(setters.setConfirmationData).toHaveBeenCalledWith(data);
    expect(setters.setShowConfirmation).toHaveBeenCalledWith(true);
    // 不能触发其他 modal
    expect(setters.setShowQuestionnaire).not.toHaveBeenCalled();
  });

  // ── 互斥性：每次只打开一个 modal ──
  it('每次 dispatch 只激活唯一 modal（互斥性）', () => {
    dispatch({ interaction_type: 'user_question' });
    const openCalls = [
      setters.setShowQuestionnaire,
      setters.setShowRoleTaskReview,
      setters.setShowUserQuestion,
      setters.setShowQualityPreflight,
      setters.setShowConfirmation,
    ].filter((fn) => fn.mock.calls.some(([v]) => v === true));
    expect(openCalls.length).toBe(1);
  });
});
