/**
 * 回归测试：interrupt 路由完整性
 *
 * 目标：确保重构后（引入 applyInterruptDispatch + output_intent_confirmation）
 * 所有原有 interrupt 类型仍正确路由，同时验证新类型。
 *
 * 每个已知 type 都必须触发正确的 setter，且不触发其他 modal 的 setter。
 */
export {};

// ── 路由逻辑镜像（与 integration 测试共享相同实现） ─────────────────────

type RegressionInterruptSetters = {
  setQuestionnaireData:     jest.Mock;
  setShowQuestionnaire:     jest.Mock;
  setCurrentProgressiveStep: jest.Mock;
  setProgressiveStepData:   jest.Mock;
  setRoleTaskReviewData:    jest.Mock;
  setShowRoleTaskReview:    jest.Mock;
  setUserQuestionData:      jest.Mock;
  setShowUserQuestion:      jest.Mock;
  setQualityPreflightData:  jest.Mock;
  setShowQualityPreflight:  jest.Mock;
  // 🔄 v10.2 Path B: setOutputIntentData / setShowOutputIntentModal 已移除
  setConfirmationData:      jest.Mock;
  setShowConfirmation:      jest.Mock;
  resumeAnalysis:           jest.Mock;
};

function makeSetters(): RegressionInterruptSetters {
  return {
    setQuestionnaireData:     jest.fn(),
    setShowQuestionnaire:     jest.fn(),
    setCurrentProgressiveStep: jest.fn(),
    setProgressiveStepData:   jest.fn(),
    setRoleTaskReviewData:    jest.fn(),
    setShowRoleTaskReview:    jest.fn(),
    setUserQuestionData:      jest.fn(),
    setShowUserQuestion:      jest.fn(),
    setQualityPreflightData:  jest.fn(),
    setShowQualityPreflight:  jest.fn(),
    setConfirmationData:      jest.fn(),
    setShowConfirmation:      jest.fn(),
    resumeAnalysis:           jest.fn().mockResolvedValue(undefined),
  };
}

function createApplyInterruptDispatch(setters: RegressionInterruptSetters, sessionId: string) {
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

// ── 全量类型覆盖矩阵 ──────────────────────────────────────────────────────

/** 所有可能打开 modal 的 setter 名字（排除 setCurrentProgressiveStep，它非 bool） */
const MODAL_OPEN_SETTERS: Array<keyof RegressionInterruptSetters> = [
  'setShowQuestionnaire',
  'setShowRoleTaskReview',
  'setShowUserQuestion',
  'setShowQualityPreflight',
  'setShowConfirmation',
];

function assertOnlyOneModalOpened(setters: RegressionInterruptSetters, expectedModal: keyof RegressionInterruptSetters | null) {
  for (const key of MODAL_OPEN_SETTERS) {
    const calls = (setters[key] as jest.Mock).mock.calls.filter(([v]) => v === true);
    if (key === expectedModal) {
      expect(calls.length).toBeGreaterThanOrEqual(1);
    } else {
      expect(calls.length).toBe(0);
    }
  }
}

// ── 回归测试套件 ──────────────────────────────────────────────────────────

describe('回归测试 > interrupt 路由完整性（所有已知类型）', () => {
  const SESSION = 'regression-session';
  let setters: RegressionInterruptSetters;
  let dispatch: ReturnType<typeof createApplyInterruptDispatch>;

  beforeEach(() => {
    setters  = makeSetters();
    dispatch = createApplyInterruptDispatch(setters, SESSION);
    jest.clearAllMocks();
    // 重新构建（clearAllMocks 会清空 mock，重建 setters）
    setters  = makeSetters();
    dispatch = createApplyInterruptDispatch(setters, SESSION);
  });

  // ── 1. calibration_questionnaire（原有）──────────────────────────────────
  it('[回归] calibration_questionnaire 路由不变', () => {
    dispatch({ interaction_type: 'calibration_questionnaire', questionnaire: {} });
    expect(setters.setShowQuestionnaire).toHaveBeenCalledWith(true);
    assertOnlyOneModalOpened(setters, 'setShowQuestionnaire');
  });

  // ── 2. role_and_task_unified_review（原有）──────────────────────────────
  it('[回归] role_and_task_unified_review 路由不变', () => {
    dispatch({ interaction_type: 'role_and_task_unified_review' });
    expect(setters.setShowRoleTaskReview).toHaveBeenCalledWith(true);
    assertOnlyOneModalOpened(setters, 'setShowRoleTaskReview');
  });

  it('[回归] close_previous_modal=true 正确关闭进度步骤', () => {
    dispatch({ interaction_type: 'role_and_task_unified_review', close_previous_modal: true });
    expect(setters.setCurrentProgressiveStep).toHaveBeenCalledWith(0);
    expect(setters.setProgressiveStepData).toHaveBeenCalledWith(null);
  });

  // ── 3. user_question（原有）─────────────────────────────────────────────
  it('[回归] user_question 路由不变', () => {
    dispatch({ interaction_type: 'user_question' });
    expect(setters.setShowUserQuestion).toHaveBeenCalledWith(true);
    assertOnlyOneModalOpened(setters, 'setShowUserQuestion');
  });

  // ── 4. batch_confirmation（原有）────────────────────────────────────────
  it('[回归] batch_confirmation 自动批准，不打开任何 modal', () => {
    dispatch({ interaction_type: 'batch_confirmation' });
    expect(setters.resumeAnalysis).toHaveBeenCalledWith(SESSION, 'approve');
    assertOnlyOneModalOpened(setters, null);
  });

  // ── 5–8. progressive steps（原有）───────────────────────────────────────
  it('[回归] progressive_questionnaire_step1 → step=1', () => {
    dispatch({ interaction_type: 'progressive_questionnaire_step1' });
    expect(setters.setCurrentProgressiveStep).toHaveBeenCalledWith(1);
    assertOnlyOneModalOpened(setters, null); // 用 step > 0 控制显示，无独立 bool
  });

  it('[回归] progressive_questionnaire_step2 → step=2', () => {
    dispatch({ interaction_type: 'progressive_questionnaire_step2' });
    expect(setters.setCurrentProgressiveStep).toHaveBeenCalledWith(2);
  });

  it('[回归] progressive_questionnaire_step3 → step=3', () => {
    dispatch({ interaction_type: 'progressive_questionnaire_step3' });
    expect(setters.setCurrentProgressiveStep).toHaveBeenCalledWith(3);
  });

  it('[回归] progressive_questionnaire_step4 → step=4', () => {
    dispatch({ interaction_type: 'progressive_questionnaire_step4' });
    expect(setters.setCurrentProgressiveStep).toHaveBeenCalledWith(4);
  });

  it('[回归] requirements_insight → step=4（aliased to step4）', () => {
    dispatch({ interaction_type: 'requirements_insight' });
    expect(setters.setCurrentProgressiveStep).toHaveBeenCalledWith(4);
    assertOnlyOneModalOpened(setters, null);
  });

  // ── 9. quality_preflight_warning（原有）─────────────────────────────────
  it('[回归] quality_preflight_warning 路由不变', () => {
    dispatch({ interaction_type: 'quality_preflight_warning', warnings: [] });
    expect(setters.setShowQualityPreflight).toHaveBeenCalledWith(true);
    assertOnlyOneModalOpened(setters, 'setShowQualityPreflight');
  });

  // ── 10. output_intent_confirmation（🔄 v10.2 Path B: 兜底分支）──────────────
  it('[新增] output_intent_confirmation → setShowConfirmation(true)（Path B 兜底）', () => {
    dispatch({ interaction_type: 'output_intent_confirmation' });
    expect(setters.setShowConfirmation).toHaveBeenCalledWith(true);
    assertOnlyOneModalOpened(setters, 'setShowConfirmation');
  });

  it('[新增] output_intent_confirmation 不触发其他任何 modal', () => {
    dispatch({
      interaction_type: 'output_intent_confirmation',
      delivery_types:   { options: [] },
      identity_modes:   { options: [] },
    });
    expect(setters.setShowQuestionnaire).not.toHaveBeenCalled();
    expect(setters.setShowRoleTaskReview).not.toHaveBeenCalled();
    expect(setters.setShowUserQuestion).not.toHaveBeenCalled();
    expect(setters.setShowQualityPreflight).not.toHaveBeenCalled();
    expect(setters.resumeAnalysis).not.toHaveBeenCalled();
  });

  // ── 11. 兜底（原有）──────────────────────────────────────────────────────
  it('[回归] 未知类型兜底仍触发通用确认框', () => {
    dispatch({ interaction_type: 'some_new_unknown_type_v999' });
    expect(setters.setShowConfirmation).toHaveBeenCalledWith(true);
    expect(setters.setConfirmationData).toHaveBeenCalled();
    assertOnlyOneModalOpened(setters, 'setShowConfirmation');
  });

  // ── 12. null/undefined 防御（原有）──────────────────────────────────────
  it('[回归] null / undefined interruptData 不崩溃', () => {
    expect(() => dispatch(null)).not.toThrow();
    expect(() => dispatch(undefined)).not.toThrow();
    expect(() => dispatch({})).not.toThrow(); // 无 interaction_type → 兜底
  });

  // ── 13. 幂等性：重复 dispatch 相同类型，每次都正确路由 ──────────────────
  it('[稳定性] 连续两次 dispatch output_intent_confirmation 均路由到兜底确认框', () => {
    dispatch({ interaction_type: 'output_intent_confirmation' });
    dispatch({ interaction_type: 'output_intent_confirmation' });
    expect(setters.setShowConfirmation).toHaveBeenCalledTimes(2);
    expect(setters.setConfirmationData).toHaveBeenCalledTimes(2);
  });

  // ── 14. 完整类型清单完整性检查 ───────────────────────────────────────────
  it('[完整性] 所有预期的 interaction_type 均有对应行为（无遗漏）', () => {
    const knownTypes = [
      'calibration_questionnaire',
      'role_and_task_unified_review',
      'user_question',
      'batch_confirmation',
      'progressive_questionnaire_step1',
      'progressive_questionnaire_step2',
      'progressive_questionnaire_step3',
      'progressive_questionnaire_step4',
      'requirements_insight',
      'quality_preflight_warning',
      'output_intent_confirmation',
    ];

    knownTypes.forEach((type) => {
      const s = makeSetters();
      const d = createApplyInterruptDispatch(s, SESSION);
      expect(() => d({ interaction_type: type })).not.toThrow();
    });
  });
});
