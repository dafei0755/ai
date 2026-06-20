import type { ChatMessage } from '@/components/ConversationMode/ConversationChat';

export type ConversationHistoryEntry = {
  role?: string;
  content?: string;
  timestamp?: string;
  guidance_card?: ChatMessage['guidance_card'];
  in_response_to_card_id?: string;
  selected_option_id?: string;
};

export const resolveGuidanceSelectionLabel = (
  card: ChatMessage['guidance_card'] | undefined,
  optionId?: string,
  freetext?: string,
) => {
  if (freetext && !freetext.startsWith('[card:')) return freetext;
  if (!card || !optionId) return undefined;
  const allOptions = [
    ...(card.options ?? []),
    ...(card.pages ?? []).flatMap((page) => page.options ?? []),
    ...(card.version_cards ?? []).map((version) => ({
      id: version.id,
      label: version.name,
      description: version.subtitle,
    })),
  ];
  const opt = allOptions.find((item) => item.id === optionId);
  if (!opt) return optionId;
  return opt.description ? `${opt.label}：${opt.description}` : opt.label;
};

export const buildConversationMessagesFromHistory = (history?: ConversationHistoryEntry[]): ChatMessage[] => {
  const messages: ChatMessage[] = [];
  for (const entry of history ?? []) {
    const role = entry.role === 'assistant' ? 'assistant' : entry.role === 'user' ? 'user' : null;
    if (!role) continue;

    const legacyCardMatch = role === 'user' ? entry.content?.match(/^\[card:([^\]]+)\]$/) : null;
    const responseCardId = entry.in_response_to_card_id;
    const previousCardMessage = [...messages]
      .reverse()
      .find((message) => message.role === 'assistant' && message.guidance_card && !message.card_responded);
    if (role === 'user' && (responseCardId || (legacyCardMatch && previousCardMessage))) {
      const targetCardId = responseCardId || previousCardMessage?.guidance_card?.card_id;
      const selectedOptionId = entry.selected_option_id || legacyCardMatch?.[1];
      const targetIndex = messages.findIndex(
        (message) => message.guidance_card?.card_id === targetCardId,
      );
      if (targetIndex >= 0) {
        const target = messages[targetIndex];
        messages[targetIndex] = {
          ...target,
          card_responded: true,
          card_selection_label: resolveGuidanceSelectionLabel(
            target.guidance_card,
            selectedOptionId,
            entry.content,
          ),
        };
      }
      continue;
    }

    if (!entry.content) continue;
    messages.push({
      id: `history-${messages.length}-${entry.timestamp ?? Date.now()}`,
      role,
      content: entry.content,
      timestamp: entry.timestamp ?? new Date().toISOString(),
      guidance_card: role === 'assistant' ? entry.guidance_card : undefined,
    });
  }
  return messages;
};

export const hydrateMissingGuidanceCards = (
  restoredMessages: ChatMessage[],
  initialMessages: ChatMessage[],
): ChatMessage[] => {
  if (restoredMessages.length === 0 || initialMessages.length === 0) return restoredMessages;
  const initialAssistantCards = initialMessages
    .filter((message) => message.role === 'assistant' && message.guidance_card)
    .map((message) => message.guidance_card);
  if (initialAssistantCards.length === 0) return restoredMessages;

  let assistantIndex = 0;
  return restoredMessages.map((message) => {
    if (message.role !== 'assistant') return message;
    const fallbackCard = initialAssistantCards[assistantIndex];
    assistantIndex += 1;
    if (message.guidance_card || !fallbackCard) return message;
    return { ...message, guidance_card: fallbackCard };
  });
};

