import { writable } from 'svelte/store';

/**
 * A Svelte store that holds a Set of all known Task class names in the current graph.
 * This is used by TaskNode to populate the type dropdown, allowing fields to reference
 * other defined Task classes.
 */
export const taskClassNamesStore = writable<Set<string>>(new Set());
