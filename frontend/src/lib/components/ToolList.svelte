<script lang="ts">
	import {
		tools as toolsStore,
		addTool,
		removeTool,
		type Tool
	} from '$lib/stores/toolStore.svelte';
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
	}

	function deleteTool(tool: Tool) {
		removeTool(tool);
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
				<div
					class="group flex items-center justify-between rounded border-l-4 p-2 shadow-sm"
					style="border-left-color: {color}; background-color: {color}1A;"
				>
					<div class="flex-grow">
						<h3 class="text-sm font-semibold text-gray-800">{tool.name}</h3>
						<p class="text-xs text-gray-600">{tool.description}</p>
					</div>
					<button
						class="ml-2 flex h-6 w-6 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity hover:bg-red-100 hover:text-red-600 group-hover:opacity-100"
						onclick={() => deleteTool(tool)}
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
