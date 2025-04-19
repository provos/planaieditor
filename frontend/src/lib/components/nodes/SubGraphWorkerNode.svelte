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
			outputTypes: ['FinalPlan']
		},
		{
			name: 'create_search_fetch_worker',
			inputTypes: ['SearchQuery'],
			outputTypes: ['ConsolidatedPages']
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

	const updateNodeInternals = useUpdateNodeInternals();

	// --- State for Factory Function Editing ---
	let editingFactoryFunction = $state(false);
	// tempFactoryFunction now stores just the name for the select binding
	let tempFactoryFunction = $state(data.factoryFunction || availableFactoryFunctions[0].name);

	function startEditingFactory() {
		tempFactoryFunction = data.factoryFunction || availableFactoryFunctions[0].name;
		editingFactoryFunction = true;
	}

	function updateFactoryFunction(event: Event) {
		const select = event.target as HTMLSelectElement;
		if (select.value) {
			console.log('updateFactoryFunction', select.value);
			const selectedFactory = availableFactoryFunctions.find(
				(f) => f.name === select.value
			);
			if (selectedFactory) {
				data = {
					...data,
					factoryFunction: selectedFactory.name,
					inputTypes: selectedFactory.inputTypes,
					output_types: selectedFactory.outputTypes
				};
			} else {
				// Handle case where factory function might be invalid or unset
				data = {
					...data,
					factoryFunction: undefined,
					inputTypes: [],
					output_types: []
				};
			}
			tick().then(() => updateNodeInternals(id));
		}
		editingFactoryFunction = false;
	}

	function cancelEditingFactory() {
		editingFactoryFunction = false;
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
	{data}
	defaultName={data.factoryFunction || 'SubGraphWorker'}
	isCached={data.isCached}
	minWidth={200}
	minHeight={150}
	outputTypesEditable={false}
>
	<div class="mt-1 flex flex-col rounded bg-blue-50 p-1 text-blue-700">
		<div class="text-2xs mb-1 flex flex-none items-center">
			<CodeSimple size={10} weight="bold" class="mr-1 flex-none" />
			{#if editingFactoryFunction}
				<select
					bind:value={tempFactoryFunction}
					onchange={updateFactoryFunction}
					onblur={cancelEditingFactory}
					class="text-2xs font-mono font-semibold"
				>
					{#each availableFactoryFunctions as func}
						<option value={func.name}>{func.name}</option>
					{/each}
				</select>
			{:else}
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<span
					class="cursor-pointer rounded px-1 font-mono font-semibold hover:bg-blue-100"
					onclick={startEditingFactory}
					role="button"
					tabindex="0"
				>
					Factory: {data.factoryFunction}
				</span>
			{/if}
		</div>
		{#if data.factoryInvocation !== undefined}
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
		{/if}
	</div>
	<!-- Any additional content specific to SubGraphWorker can go here -->
	<!-- BaseWorkerNode already displays input/output types -->
	<!-- BaseWorkerNode will now hide editing controls because outputTypesEditable is false -->
</BaseWorkerNode>

<style>
	/* Styles specific to SubGraphWorkerNode if needed */
	:global(.text-2xs) {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
