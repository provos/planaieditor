import { persistedState } from '$lib/utils/persist.svelte';
import { untrack } from 'svelte';
import { toolNamesStore } from './classNameStore.svelte';

export interface Tool {
	id: string;
	name: string;
	description: string;
	code: string;
	_lastUpdated?: number;
}

export const tools = persistedState<Tool[]>('tools', [], { storage: 'local' });

export function addTool(tool: Tool) {
	tools.push(tool);
}

export function removeTool(tool: Tool) {
	tools.splice(tools.indexOf(tool), 1);
}

export function updateTool(tool: Tool) {
	const index = tools.findIndex((t) => t.id === tool.id);
	if (index !== -1) {
		tools[index] = tool;
	}
}

export function getToolByName(name: string): Tool | undefined {
	return tools.find((tool: Tool) => tool.name === name);
}

export function getToolById(id: string): Tool | undefined {
	return tools.find((tool: Tool) => tool.id === id);
}

// Update the tool names store when the tools change
$effect.root(() => {
	$effect(() => {
		const toolNames = new Set(tools.map((tool: Tool) => tool.name));
		untrack(() => {
			toolNamesStore.clear();
			toolNames.forEach((name) => toolNamesStore.add(name));
		});
	});
});
