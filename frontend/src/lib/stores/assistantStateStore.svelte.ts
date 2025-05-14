interface AssistantState {
    isOpen: boolean;
}

export const assistantState = $state<AssistantState>({
    isOpen: false,
});

export function openAssistant() {
    assistantState.isOpen = true;
}

export function closeAssistant() {
    assistantState.isOpen = false;
}