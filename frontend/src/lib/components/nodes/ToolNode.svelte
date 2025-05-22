<script lang="ts">
	import HeaderIcon from '$lib/components/HeaderIcon.svelte';

	export interface ToolNodeData {
		name: string;
		description: string | null;
		code: string;
		nodeId: string; // Should be populated with the node's id
	}

	let { id, data } = $props<{
		id: string;
		data: ToolNodeData;
	}>();
</script>

<div
	class="tool-node flex h-full flex-col overflow-auto rounded-md border border-gray-300 bg-white shadow-md"
>
	<div class="flex-none border-b bg-yellow-100 p-1">
		<HeaderIcon workerType={'tool'} />
		<div
			class="w-full cursor-pointer rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-yellow-50"
		>
			Tool Library
		</div>
	</div>
	<div class="flex-none p-1.5">
		<div class="prose prose-xs max-w-xs">
			<p>Click on this node to open the tool library where you can add, edit, and delete tools.</p>
		</div>
	</div>
</div>
