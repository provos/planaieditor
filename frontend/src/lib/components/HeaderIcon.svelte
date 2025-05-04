<script lang="ts">
    import { getNodeIconStyle } from '$lib/utils/defaults';

    let { workerType } = $props<{ workerType: string }>();

    const nodeIconStyle = getNodeIconStyle(workerType || 'default');

    const workerTypeMap = {
        'llmtaskworker': 'LLMTaskWorker',
        'taskworker': 'TaskWorker',
        'joinedtaskworker': 'JoinedTaskWorker',
        'modulelevelimport': 'ModuleLevelImport',
        'dataoutput': 'DataOutput',
        'datainput': 'DataInput',
        'subgraphworker': 'SubgraphWorker',
        'chattaskworker': 'ChatTaskWorker',
    }

    const workerTypeLabel = workerTypeMap[workerType as keyof typeof workerTypeMap] || workerType;

</script>

<div class="absolute left-1.5 top-1.5 z-10 flex items-center justify-between">
    <nodeIconStyle.icon size={16} weight="fill" class={nodeIconStyle.color}/>
    <div class="text-sm font-light text-gray-700/50 relative -top-0.5">
        {workerTypeLabel}
    </div>
</div>
