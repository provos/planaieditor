<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import type { BaseWorkerData as WorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte'; // Correct import

	let { id, data } = $props<{
		id: string;
		data: WorkerData;
	}>();

	// Handler for code updates
	function handleCodeUpdate(newCode: string) {
		data.consumeWork = newCode;
	}
</script>

<BaseWorkerNode {id} {data} defaultName="TaskWorker">
	<div class="flex min-h-0 flex-grow flex-col overflow-hidden">
		<EditableCodeSection
			title="consume_work()"
			code={data.consumeWork}
			language="python"
			onUpdate={handleCodeUpdate}
		/>
	</div>
</BaseWorkerNode>
