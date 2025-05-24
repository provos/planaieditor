import { persistedState } from '$lib/utils/persist.svelte';
import { toolNamesStore } from './classNameStore.svelte';

export interface Tool {
	id: string;
	name: string;
	description: string;
	code: string;
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

// Update the tool names store when the tools change
$effect.root(() => {
	$effect(() => {
		const toolNames = new Set(tools.map((tool: Tool) => tool.name));
		toolNamesStore.clear();
		toolNames.forEach((name) => toolNamesStore.add(name));
	});
});
