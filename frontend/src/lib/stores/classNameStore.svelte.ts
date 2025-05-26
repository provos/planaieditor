import { SvelteSet, SvelteMap } from 'svelte/reactivity';

// Create a global store for tracking all class names
// Maps nodeId -> className
export const allWorkerClassNames = $state<SvelteMap<string, string>>(new SvelteMap());

/**
 * A Svelte 5 rune that holds a Set of all known Task class names in the current graph.
 * This is used by TaskNode to populate the type dropdown, allowing fields to reference
 * other defined Task classes.
 */
export const taskClassNamesStore = $state<SvelteSet<string>>(new SvelteSet());

/**
 * A Svelte 5 rune that holds a Set of all known Tool names in the current graph.
 * This is used by ToolNode to populate the type dropdown, allowing fields to reference
 * other defined Tool functions.
 */
export const toolNamesStore = $state<SvelteSet<string>>(new SvelteSet());
