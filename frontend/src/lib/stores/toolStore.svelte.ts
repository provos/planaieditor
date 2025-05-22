interface Tool {
	id: string;
	name: string;
	description: string;
	code: string;
}

export const tools = $state<Tool[]>([]);

export function addTool(tool: Tool) {
	tools.push(tool);
}

export function removeTool(tool: Tool) {
	tools.splice(tools.indexOf(tool), 1);
}

export function updateTool(tool: Tool) {
	tools[tools.indexOf(tool)] = tool;
}