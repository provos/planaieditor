import { writable } from 'svelte/store';
import { persisted } from 'svelte-persisted-store';

interface AssistantState {
	isOpen: boolean;
}

interface Message {
	type: 'user' | 'assistant';
	content: string;
	timestamp: Date;
}

export const assistantState = $state<AssistantState>({
	isOpen: false
});

export function openAssistant() {
	assistantState.isOpen = true;
}

export function closeAssistant() {
	assistantState.isOpen = false;
}

export const assistantResponse = writable<string | null>(null);

// Persisted store for chat messages
export const assistantMessages = persisted<Message[]>('assistantMessages', []);

// Function to clear chat messages
export function clearAssistantMessages() {
	assistantMessages.set([]);
}
