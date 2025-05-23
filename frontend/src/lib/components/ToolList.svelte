<script lang="ts">
	import {
		tools as toolsStore,
		addTool,
		removeTool,
		type Tool
	} from '$lib/stores/toolStore.svelte';
	import { splitPaneConfig } from '$lib/stores/splitPaneStore.svelte';
	import BaseList from './BaseList.svelte';

	function createNewTool() {
		const newTool: Tool = {
			id: `tool-${Date.now()}`,
			name: 'New Tool',
			description: 'Enter tool description',
			code: `def new_tool_function():\n    pass`
		};
		addTool(newTool);
		splitPaneConfig.upperNodeId = newTool.id;
		splitPaneConfig.upperNodeType = 'tool';
	}

	function deleteTool(tool: Tool) {
		removeTool(tool);
		if (splitPaneConfig.upperNodeId === tool.id) {
			splitPaneConfig.upperNodeId = null;
			splitPaneConfig.upperNodeType = null;
		}
	}

	function selectTool(tool: Tool) {
		splitPaneConfig.upperNodeId = tool.id;
		splitPaneConfig.upperNodeType = 'tool';
	}

	function isToolSelected(tool: Tool): boolean {
		return splitPaneConfig.upperNodeId === tool.id && splitPaneConfig.upperNodeType === 'tool';
	}
</script>

<BaseList
	items={toolsStore}
	onSelect={selectTool}
	onDelete={deleteTool}
	onCreate={createNewTool}
	emptyMessage="No tools defined yet. Click the plus button below to add one."
	createButtonTitle="Add new tool"
	getName={(tool) => tool.name}
	getDescription={(tool) => tool.description}
	getId={(tool) => tool.id}
	isSelected={isToolSelected}
/>
