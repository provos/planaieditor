<script lang="ts">
	import { splitPaneConfig } from '$lib/stores/splitPaneStore.svelte';
	import ToolConfig from './ToolConfig.svelte';
	import TaskConfig from './TaskConfig.svelte';
	import TaskImportConfig from './TaskImportConfig.svelte';

	const upperNodeId = $derived(splitPaneConfig.upperNodeId);
	const upperNodeType = $derived(splitPaneConfig.upperNodeType);
</script>

<div class="h-full overflow-auto border border-gray-300 bg-gray-200 p-2">
	{#key upperNodeId}
		{#if upperNodeType === 'tool' && upperNodeId}
			<ToolConfig id={upperNodeId} />
		{:else if upperNodeType === 'task' && upperNodeId}
			<TaskConfig id={upperNodeId} />
		{:else if upperNodeType === 'taskimport' && upperNodeId}
			<TaskImportConfig id={upperNodeId} />
		{:else}
			<div
				class="flex h-full items-center justify-center rounded border-t border-gray-200 bg-white"
			>
				<p class="text-sm text-gray-500 italic">
					Click on a tool, task, or task import in the list at the bottom to edit it.
				</p>
			</div>
		{/if}
	{/key}
</div>
