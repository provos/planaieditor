<script lang="ts">
	import { getNodeIconStyle } from '$lib/utils/defaults';

	let { workerType, extraText } = $props<{ workerType: string; extraText?: string }>();

	const nodeIconStyle = getNodeIconStyle(workerType || 'default');

	const workerTypeMap = {
		llmtaskworker: 'LLMTaskWorker',
		taskworker: 'TaskWorker',
		joinedtaskworker: 'JoinedTaskWorker',
		modulelevelimport: 'ModuleLevelImport',
		dataoutput: 'DataOutput',
		datainput: 'DataInput',
		subgraphworker: 'SubgraphWorker',
		chattaskworker: 'ChatTaskWorker'
	};

	const workerTypeLabel = workerTypeMap[workerType as keyof typeof workerTypeMap] || workerType;
</script>

<div class="absolute top-1.5 left-1.5 z-10 flex items-center justify-between">
	<nodeIconStyle.icon size={16} weight="fill" class={nodeIconStyle.color} />
	<div class="relative -top-0.5 text-sm font-light text-gray-700/50">
		{workerTypeLabel}
		{extraText}
	</div>
</div>
