<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import CodeSimple from 'phosphor-svelte/lib/CodeSimple';

	export interface SubGraphWorkerData extends BaseWorkerData {
		isFactoryCreated?: boolean;
		factoryFunction?: string; // Name of the factory function
	}

	let { id, data } = $props<{
		id: string;
		data: SubGraphWorkerData;
	}>();

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
		<div class="text-2xs mt-1 flex flex-none items-center rounded bg-blue-50 p-1 text-blue-700">
			<CodeSimple size={10} weight="bold" class="mr-1 flex-none" />
			<span class="font-mono font-semibold">Factory: {data.factoryFunction}</span>
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
