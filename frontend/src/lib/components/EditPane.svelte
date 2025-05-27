<script lang="ts">
	import { splitPaneConfig } from '$lib/stores/splitPaneStore.svelte';
	import { tools as toolsStore } from '$lib/stores/toolStore.svelte';
	import TaskConfig from './TaskConfig.svelte';
	import TaskImportConfig from './TaskImportConfig.svelte';
	import ToolConfig from './ToolConfig.svelte';

	const upperNodeId = $derived(splitPaneConfig.upperNodeId);
	const upperNodeType = $derived(splitPaneConfig.upperNodeType);

	// Get the tool's _lastUpdated for keying when editing tools
	const selectedTool = $derived(
		upperNodeType === 'tool' && upperNodeId
			? toolsStore.find((t) => t.id === upperNodeId)
			: undefined
	);
	const toolLastUpdated = $derived(selectedTool?._lastUpdated || 0);
</script>

<div class="h-full overflow-auto border border-gray-300 bg-gray-200 p-2">
	{#if upperNodeType === 'tool' && upperNodeId}
		{#key `${upperNodeId}-${toolLastUpdated}`}
			<ToolConfig id={upperNodeId} />
		{/key}
	{:else}
		{#key upperNodeId}
			{#if upperNodeType === 'task' && upperNodeId}
				<TaskConfig id={upperNodeId} />
			{:else if upperNodeType === 'taskimport' && upperNodeId}
				<TaskImportConfig id={upperNodeId} />
			{:else}
				<div
					class="flex h-full items-center justify-center rounded border-t border-gray-200 bg-white"
				>
					<p class="p-2 text-center text-sm text-gray-500 italic">
						Click on a tool, task, or task import in the list at the bottom to edit it.
					</p>
				</div>
			{/if}
		{/key}
	{/if}
</div>
