import { writable } from 'svelte/store';

// Create a global store for tracking all class names
// Maps nodeId -> className
export const allClassNames = writable<Map<string, string>>(new Map());
