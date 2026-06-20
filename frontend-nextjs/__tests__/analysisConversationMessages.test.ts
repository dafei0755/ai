import {
  buildConversationMessagesFromHistory,
  hydrateMissingGuidanceCards,
} from '@/lib/analysisConversationMessages';
import type { ChatMessage } from '@/components/ConversationMode/ConversationChat';

const demandReconstructionCard: NonNullable<ChatMessage['guidance_card']> = {
  card_id: 'demand-reconstruction-001',
  card_type: 'demand_reconstruction_blueprint',
  title: '需求重构',
  prompt_text: '先判断真实需求。',
  options: [],
  summary: {
    insight_source: 'semantic_fallback',
    llm_status: 'not_configured',
  },
};

it('builds enhanced demand reconstruction messages from backend history', () => {
  const messages = buildConversationMessagesFromHistory([
    { role: 'user', content: '苏州昆曲故居改造', timestamp: '2026-06-18T08:47:00.000Z' },
    {
      role: 'assistant',
      content: 'LLM enhanced answer',
      timestamp: '2026-06-18T08:48:00.000Z',
      guidance_card: {
        ...demandReconstructionCard,
        summary: {
          insight_source: 'llm',
          llm_status: 'used',
        },
      },
    },
  ]);

  expect(messages).toHaveLength(2);
  expect(messages[1].content).toBe('LLM enhanced answer');
  expect(messages[1].guidance_card?.summary?.insight_source).toBe('llm');
  expect(messages[1].guidance_card?.summary?.llm_status).toBe('used');
});

it('hydrates restored assistant messages with the initial guidance card when history omits it', () => {
  const restored = buildConversationMessagesFromHistory([
    { role: 'user', content: '苏州昆曲故居改造', timestamp: '2026-06-18T08:47:00.000Z' },
    { role: 'assistant', content: 'Restored answer without card', timestamp: '2026-06-18T08:47:01.000Z' },
  ]);
  const initial: ChatMessage[] = [
    { id: 'u1', role: 'user', content: '苏州昆曲故居改造', timestamp: '2026-06-18T08:47:00.000Z' },
    { id: 'a1', role: 'assistant', content: 'Initial answer', timestamp: '2026-06-18T08:47:01.000Z', guidance_card: demandReconstructionCard },
  ];

  const hydrated = hydrateMissingGuidanceCards(restored, initial);

  expect(hydrated[1].guidance_card?.card_id).toBe('demand-reconstruction-001');
  expect(hydrated[1].guidance_card?.summary?.llm_status).toBe('not_configured');
});
