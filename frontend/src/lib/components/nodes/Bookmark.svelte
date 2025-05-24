<script lang="ts">
	import HeaderIcon from '$lib/components/HeaderIcon.svelte';
	import { splitPaneConfig, openSplitPane } from '$lib/stores/splitPaneStore.svelte';

	let { id, data, type, title, description } = $props<{
		id: string;
		data: any;
		type: 'tool' | 'task' | 'taskimport';
		title: string;
		description: string;
	}>();

	// Define color mappings based on type
	const colorMap = {
		tool: { bg: 'bg-yellow-100', hover: 'hover:bg-yellow-50' },
		task: { bg: 'bg-blue-100', hover: 'hover:bg-blue-50' },
		taskimport: { bg: 'bg-purple-100', hover: 'hover:bg-purple-50' }
	};

	const colors = colorMap[type as keyof typeof colorMap];

	function handleNodeClick() {
		// Set the selected node to activate the appropriate tab in ListPane
		splitPaneConfig.selectedNodeId = id;
		openSplitPane();
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
	class="{type}-node flex h-full cursor-pointer flex-col overflow-auto rounded-md border border-gray-300 bg-white shadow-md"
	onclick={handleNodeClick}
	role="button"
	tabindex="0"
>
	<div class="flex-none border-b {colors.bg} p-1">
		<HeaderIcon workerType={type} />
		<div class="w-full rounded px-1 py-0.5 text-center text-xs font-medium {colors.hover}">
			{title}
		</div>
	</div>
	<div class="flex-none p-1.5">
		<div class="prose prose-xs max-w-xs">
			<p>{description}</p>
		</div>
	</div>
</div>
