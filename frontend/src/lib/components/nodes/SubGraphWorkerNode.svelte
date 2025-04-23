<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import CodeSimple from 'phosphor-svelte/lib/CodeSimple';
	import EditableCodeSection from '../EditableCodeSection.svelte';
	import { useUpdateNodeInternals } from '@xyflow/svelte';
	import { tick } from 'svelte';

	// Define available factory functions with their types
	const availableFactoryFunctions = [
		{
			name: 'create_planning_worker',
			inputTypes: ['PlanRequest'],
			outputTypes: ['FinalPlan'],
			className: 'PlanningWorkerSubgraph'
		},
		{
			name: 'create_search_fetch_worker',
			inputTypes: ['SearchQuery'],
			outputTypes: ['ConsolidatedPages'],
			className: 'SearchFetchWorker'
		}
	];

	export interface SubGraphWorkerData extends BaseWorkerData {
		isFactoryCreated?: boolean;
		factoryFunction?: string; // Name of the factory function
		factoryInvocation?: string; // Combined invocation string
	}

	let { id, data } = $props<{
		id: string;
		data: SubGraphWorkerData;
	}>();

	let dataCopy = $state(data);
	const updateNodeInternals = useUpdateNodeInternals();
	// Use a temporary variable to store the currently selected factory function
	let selectedFactoryName = $state(data.factoryFunction || '');

	if (data.factoryInvocation === undefined) {
		data.factoryInvocation = '';
	}

	function updateFactoryFunction(event: Event) {
		const select = event.target as HTMLSelectElement;
		const value = select.value;

		// Only update if a factory function is actually selected
		if (value) {
			console.log('updateFactoryFunction', value);
			const selectedFactory = availableFactoryFunctions.find((f) => f.name === value);
			if (selectedFactory) {
				data.factoryFunction = selectedFactory.name;
				data.inputTypes = selectedFactory.inputTypes;
				data.output_types = selectedFactory.outputTypes;
				data.workerName = selectedFactory.className;
				// Also update our local tracking variable
				selectedFactoryName = selectedFactory.name;
			}
			dataCopy = { ...data };
			tick().then(() => updateNodeInternals(id));
		} else {
			// Handle empty selection (reset)
			console.log('resetting factory function');
			data.factoryFunction = undefined;
			data.inputTypes = [];
			data.output_types = [];
			data.workerName = undefined;
			selectedFactoryName = '';
			dataCopy = { ...data };
			tick().then(() => updateNodeInternals(id));
		}
	}

	function handleInvocationUpdate(newCode: string) {
		data.factoryInvocation = newCode;
	}

	async function handleCollapse() {
		await tick();
		updateNodeInternals(id);
	}
</script>

<BaseWorkerNode
	{id}
	data={dataCopy}
	defaultName={data.workerName || 'SubGraphWorker'}
	isCached={data.isCached}
	minWidth={200}
	minHeight={150}
	isEditable={false}
>
	<div class="mt-1 flex h-auto flex-col rounded bg-blue-50 p-1 text-blue-700">
		<div class="text-2xs mb-1 flex flex-none items-center">
			<CodeSimple size={10} weight="bold" class="mr-1 flex-none" />
			<span class="mr-1 font-mono font-semibold">Factory:</span>
			<select
				bind:value={selectedFactoryName}
				onchange={updateFactoryFunction}
				class="text-2xs rounded border-blue-200 bg-blue-50 px-1 py-0.5 font-mono"
			>
				<option value="">Select Factory...</option>
				{#each availableFactoryFunctions as func}
					<option value={func.name}>{func.name}</option>
				{/each}
			</select>
		</div>
		<div class="mt-1">
			<EditableCodeSection
				title="Arguments"
				code={data.factoryInvocation}
				language="python"
				onUpdate={handleInvocationUpdate}
				onCollapseToggle={handleCollapse}
				initialCollapsed={true}
			/>
		</div>
	</div>
</BaseWorkerNode>

<style>
	:global(.text-2xs) {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
