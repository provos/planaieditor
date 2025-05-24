// Create a global store for tracking all class names
// Maps nodeId -> className
export const allClassNames = $state<Map<string, string>>(new Map());

/**
 * A Svelte 5 rune that holds a Set of all known Task class names in the current graph.
 * This is used by TaskNode to populate the type dropdown, allowing fields to reference
 * other defined Task classes.
 */
export const taskClassNamesStore = $state<Set<string>>(new Set());

/**
 * A Svelte 5 rune that holds a Set of all known Tool names in the current graph.
 * This is used by ToolNode to populate the type dropdown, allowing fields to reference
 * other defined Tool functions.
 */
export const toolNamesStore = $state<Set<string>>(new Set());
