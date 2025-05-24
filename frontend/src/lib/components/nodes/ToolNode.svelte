<script lang="ts">
	import HeaderIcon from '$lib/components/HeaderIcon.svelte';
	import { splitPaneConfig, openSplitPane } from '$lib/stores/splitPaneStore.svelte';

	let { id, data } = $props<{
		id: string;
		data: any;
	}>();

	function handleNodeClick() {
		// Set the selected node to activate the Tool Library tab in ListPane
		splitPaneConfig.selectedNodeId = id;
		openSplitPane();
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
	class="tool-node flex h-full cursor-pointer flex-col overflow-auto rounded-md border border-gray-300 bg-white shadow-md"
	onclick={handleNodeClick}
	role="button"
	tabindex="0"
>
	<div class="flex-none border-b bg-yellow-100 p-1">
		<HeaderIcon workerType={'tool'} />
		<div class="w-full rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-yellow-50">
			Tool Library
		</div>
	</div>
	<div class="flex-none p-1.5">
		<div class="prose prose-xs max-w-xs">
			<p>Click on this node to open the tool library where you can add, edit, and delete tools.</p>
		</div>
	</div>
</div>
