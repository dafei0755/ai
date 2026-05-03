// frontend-nextjs/__tests__/mockAdvisorViewModel.test.ts
import { MOCK_ADVISOR_VIEW_MODEL } from '@/components/project-cockpit/mock/mockData';

describe('MOCK_ADVISOR_VIEW_MODEL', () => {
  it('has required traceId and generatedAt', () => {
    expect(MOCK_ADVISOR_VIEW_MODEL.traceId).toBeTruthy();
    expect(MOCK_ADVISOR_VIEW_MODEL.generatedAt).toBeTruthy();
  });

  it('has valid evidenceStatus', () => {
    expect(['none', 'internal_hint', 'verified']).toContain(
      MOCK_ADVISOR_VIEW_MODEL.evidenceStatus
    );
  });

  it('has at least one actionChip', () => {
    expect(MOCK_ADVISOR_VIEW_MODEL.actionChips.length).toBeGreaterThan(0);
  });

  it('has at most one primary chip', () => {
    const primary = MOCK_ADVISOR_VIEW_MODEL.actionChips.filter(c => c.isPrimary);
    expect(primary.length).toBeLessThanOrEqual(1);
  });

  it('has at most 2 secondary chips', () => {
    const secondary = MOCK_ADVISOR_VIEW_MODEL.actionChips.filter(c => !c.isPrimary);
    expect(secondary.length).toBeLessThanOrEqual(2);
  });

  it('has 3 activated capabilities all placeholder', () => {
    expect(MOCK_ADVISOR_VIEW_MODEL.activatedCapabilities).toHaveLength(3);
    MOCK_ADVISOR_VIEW_MODEL.activatedCapabilities.forEach(cap => {
      expect(cap.status).toBe('placeholder');
    });
  });

  it('sceneContext.module is project_base', () => {
    expect(MOCK_ADVISOR_VIEW_MODEL.sceneContext.module).toBe('project_base');
  });
});
