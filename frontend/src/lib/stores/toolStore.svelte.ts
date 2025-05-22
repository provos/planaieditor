import { persistedState } from '$lib/utils/persist.svelte';

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
	tools[tools.indexOf(tool)] = tool;
}

export function getToolByName(name: string): Tool | undefined {
	return tools.find((tool: Tool) => tool.name === name);
}
