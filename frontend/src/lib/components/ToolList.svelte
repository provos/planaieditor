<script lang="ts">
	import {
		tools as toolsStore,
		addTool,
		removeTool,
		type Tool
	} from '$lib/stores/toolStore.svelte';
	import { splitPaneConfig } from '$lib/stores/splitPaneStore.svelte';
	import { getColorForType } from '$lib/utils/colorUtils';
	import Trash from 'phosphor-svelte/lib/Trash';
	import Plus from 'phosphor-svelte/lib/Plus';

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
</script>

<div class="p-4">
	{#if toolsStore.length === 0}
		<p class="text-sm italic text-gray-500">
			No tools defined yet. Click the plus button below to add one.
		</p>
	{:else}
		<div class="space-y-2">
			{#each toolsStore as tool (tool.id)}
				{@const color = getColorForType(tool.name)}
				{@const isSelected =
					splitPaneConfig.upperNodeId === tool.id && splitPaneConfig.upperNodeType === 'tool'}
				<div
					class="group flex cursor-pointer items-center justify-between rounded border-l-4 p-2 shadow-sm transition-colors {isSelected
						? 'border-blue-500 bg-blue-100/70'
						: 'hover:bg-gray-100/50'}"
					style="border-left-color: {isSelected
						? 'transparent'
						: color}; background-color: {isSelected ? '' : color + '1A'};"
					onclick={() => selectTool(tool)}
					onkeydown={(event: KeyboardEvent) => {
						if (event.key === 'Enter' || event.key === ' ') {
							event.preventDefault(); // Prevent scrolling on spacebar
							selectTool(tool);
						}
					}}
					role="button"
					tabindex="0"
				>
					<div class="flex-grow">
						<h3 class="text-sm font-semibold {isSelected ? 'text-blue-700' : 'text-gray-800'}">
							{tool.name}
						</h3>
						<p class="text-xs {isSelected ? 'text-blue-600' : 'text-gray-600'}">
							{tool.description}
						</p>
					</div>
					<button
						class="ml-2 flex h-6 w-6 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity group-hover:opacity-100 {isSelected
							? 'text-red-500 hover:bg-red-200'
							: 'hover:bg-red-100 hover:text-red-600'}"
						onclick={(event: MouseEvent) => {
							event.stopPropagation();
							deleteTool(tool);
						}}
						title="Delete {tool.name}"
					>
						<Trash size={14} weight="bold" />
					</button>
				</div>
			{/each}
		</div>
	{/if}

	<div class="mt-4 flex justify-center">
		<button
			class="z-10 flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-blue-500 shadow-sm hover:bg-blue-200"
			onclick={createNewTool}
			title="Add new tool"
		>
			<Plus size={16} weight="bold" />
		</button>
	</div>
</div>
