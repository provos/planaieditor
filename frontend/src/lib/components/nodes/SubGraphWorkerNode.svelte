<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import CodeSimple from 'phosphor-svelte/lib/CodeSimple';
	import EditableCodeSection from '../EditableCodeSection.svelte';
	import { useUpdateNodeInternals } from '@xyflow/svelte';
	import { tick } from 'svelte';

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

	function handleInvocationUpdate(newCode: string) {
		data.factoryInvocation = newCode;
	}

	async function handleCollapse() {
		await tick();
		updateNodeInternals(id);
	}

	// Factory workers have fixed types, so no editing allowed in the UI
	// Pass necessary props to BaseWorkerNode but override editability
	// We might need to adapt BaseWorkerNode slightly to accept an `outputTypesEditable` prop
	// or hide the editing sections via slots/snippets if BaseWorkerNode supports it.
	// For now, this component simply renders the BaseWorkerNode.
	// The fixed nature is handled by not providing editing UI here and
	// relying on the BaseWorkerNode's display logic for input/output types.
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
	{#if data.factoryFunction}
		<div class="mt-1 flex flex-col rounded bg-blue-50 p-1 text-blue-700">
			<div class="text-2xs mb-1 flex flex-none items-center">
				<CodeSimple size={10} weight="bold" class="mr-1 flex-none" />
				<span class="font-mono font-semibold">Factory: {data.factoryFunction}</span>
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
	{/if}
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
