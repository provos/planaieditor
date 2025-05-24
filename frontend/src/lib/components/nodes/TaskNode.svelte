<script lang="ts">
	import HeaderIcon from '$lib/components/HeaderIcon.svelte';
	import { splitPaneConfig, openSplitPane } from '$lib/stores/splitPaneStore.svelte';

	export interface TaskNodeData {
		nodeId: string; // Should be populated with the node's id
	}

	let { id, data } = $props<{
		id: string;
		data: TaskNodeData;
	}>();

	function handleNodeClick() {
		// Set the selected node to activate the Task Definitions tab in ListPane
		splitPaneConfig.selectedNodeId = id;
		openSplitPane();
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
	class="task-node flex h-full cursor-pointer flex-col overflow-auto rounded-md border border-gray-300 bg-white shadow-md"
	onclick={handleNodeClick}
	role="button"
	tabindex="0"
>
	<div class="flex-none border-b bg-blue-100 p-1">
		<HeaderIcon workerType={'task'} />
		<div class="w-full rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-blue-50">
			Task Definitions
		</div>
	</div>
	<div class="flex-none p-1.5">
		<div class="prose prose-xs max-w-xs">
			<p>
				Click to open the task definitions pane where you can add, edit, and delete task classes.
			</p>
		</div>
	</div>
</div>
