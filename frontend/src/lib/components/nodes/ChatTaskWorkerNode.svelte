<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import LLMConfigSelector from '$lib/components/LLMConfigSelector.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import { useStore } from '@xyflow/svelte';
	import { persistNodeDataDebounced } from '$lib/utils/nodeUtils';

	export interface ChatWorkerData extends BaseWorkerData {
		llmConfigName?: string;
		llmConfigFromCode?: Record<string, any>;
		llmConfigVar?: string;
	}

	let { id, data } = $props<{
		id: string;
		data: ChatWorkerData;
	}>();

	const store = useStore();

	// Handle LLM config changes
	function handleLLMConfigChange(changes: {
		configName?: string;
		configFromCode?: Record<string, any>;
		configVar?: string;
	}) {
		data.llmConfigName = changes.configName;
		data.llmConfigFromCode = changes.configFromCode;
		data.llmConfigVar = changes.configVar;
		persistNodeDataDebounced();
	}
</script>

<BaseWorkerNode
	{id}
	{data}
	defaultName={data.workerName || 'ChatTaskWorker'}
	minWidth={200}
	minHeight={150}
	isEditable={false}
>
	<LLMConfigSelector
		{id}
		initialConfigName={data.llmConfigName}
		initialConfigFromCode={data.llmConfigFromCode}
		initialConfigVar={data.llmConfigVar}
		onChange={handleLLMConfigChange}
	/>
</BaseWorkerNode>
