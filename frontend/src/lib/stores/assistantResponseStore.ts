import { writable } from 'svelte/store';

/**
 * Stores the latest textual response from the assistant, received from the backend.
 */
export const assistantResponse = writable<string | null>(null);