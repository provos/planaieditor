<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';

	let { id, data } = $props<{
		id: string;
		data: BaseWorkerData;
	}>();
</script>

<BaseWorkerNode
	{id}
	{data}
	defaultName={data.workerName || 'ChatTaskWorker'}
	isCached={data.isCached}
	minWidth={200}
	minHeight={150}
	isEditable={false}
></BaseWorkerNode>
