<script lang="ts">
	import HeaderIcon from '$lib/components/HeaderIcon.svelte';
	import { splitPaneConfig, openSplitPane } from '$lib/stores/splitPaneStore.svelte';

	export interface TaskImportNodeData {
		nodeId: string; // Should be populated with the node's id
	}

	let { id, data } = $props<{
		id: string;
		data: TaskImportNodeData;
	}>();

	function handleNodeClick() {
		// Set the selected node to activate the Task Imports tab in ListPane
		splitPaneConfig.selectedNodeId = id;
		openSplitPane();
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
	class="taskimport-node flex h-full cursor-pointer flex-col overflow-auto rounded-md border border-gray-300 bg-white shadow-md"
	onclick={handleNodeClick}
	role="button"
	tabindex="0"
>
	<div class="flex-none border-b bg-purple-100 p-1">
		<HeaderIcon workerType={'taskimport'} />
		<div class="w-full rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-purple-50">
			Task Imports
		</div>
	</div>
	<div class="flex-none p-1.5">
		<div class="prose prose-xs max-w-xs">
			<p>
				Click to open the task imports pane where you can add, edit, and manage imported task
				classes from external modules.
			</p>
		</div>
	</div>
</div>
