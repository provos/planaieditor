<script lang="ts">
	import { NodeResizer } from '@xyflow/svelte';
	import InputHandle from '../InputHandle.svelte';
	import { tick } from 'svelte';
	import { useUpdateNodeInternals } from '@xyflow/svelte';
	import { formatErrorMessage } from '$lib/utils/utils';
	import { getColorForType } from '$lib/utils/colorUtils';
	import TrashSimple from 'phosphor-svelte/lib/TrashSimple';
	import HeaderIcon from '../HeaderIcon.svelte';
	import { persistNodeDataDebounced } from '$lib/utils/nodeUtils';
	import { type InputType } from '$lib/utils/nodeUtils';

	// Define the interface for the node's data
	export interface DataOutputNodeData {
		nodeId: string;
		receivedData?: Record<string, any>[]; // Array to store received JSON objects
		inputTypes: string[]; // Inferred input types
		error?: string; // Optional error display
	}

	// Props passed by SvelteFlow
	const { id, data } = $props<{
		id: string;
		data: DataOutputNodeData;
	}>();

	// Ensure data fields are initialized
	if (!data.receivedData) {
		data.receivedData = [];
		persistNodeDataDebounced();
	}
	if (!data.inputTypes) {
		data.inputTypes = [];
		persistNodeDataDebounced();
	}

	let receivedData = $derived<Record<string, any>[]>(data.receivedData || []);

	const updateNodeInternals = useUpdateNodeInternals();

	// --- State Variables ---
	let inferredInputTypes = $state<InputType[]>([]);

	// Callback for InputHandle to update inferred types
	function updateInferredInputTypes(updatedTypes: InputType[]) {
		inferredInputTypes = updatedTypes;
		data.inputTypes = updatedTypes.map((type) => type.className);
		persistNodeDataDebounced();
	}

	// Update node internals when content potentially changes height
	async function handleContentUpdate() {
		await tick();
		updateNodeInternals(id);
	}

	// Function to clear all received data
	function clearReceivedData() {
		receivedData = [];
		data.receivedData = [];
		persistNodeDataDebounced();
		handleContentUpdate();
	}
</script>

<div
	class="dataoutput-node flex h-full min-h-[150px] flex-col rounded-md border border-gray-300 bg-white shadow-md"
>
	<NodeResizer
		minWidth={200}
		minHeight={150}
		handleClass="resize-handle-output"
		lineClass="resize-line-output"
	/>

	<!-- Input Handle (using the reusable component) -->
	<InputHandle
		{id}
		{data}
		manuallySelectedInputType={null}
		isEditable={true}
		onUpdate={updateInferredInputTypes}
	/>

	<!-- Header with clear button -->
	<div
		class="flex-none border-b border-gray-200 bg-emerald-200 p-1 text-center text-xs font-medium"
	>
		<HeaderIcon workerType="dataoutput" />
		<div class="flex items-center justify-between">
			<div class="w-6"><!-- Spacer to balance the layout --></div>
			<div class="flex-grow">{data.workerName}</div>
			<button
				class="mt-0.5 w-4 flex-none rounded p-0.5 text-emerald-700 transition hover:bg-emerald-300/40 hover:text-emerald-900 focus:outline-none"
				title="Clear received data"
				onclick={clearReceivedData}
				aria-label="Clear data"
			>
				<TrashSimple size={12} />
			</button>
		</div>
	</div>

	<!-- Input Types Display Section -->
	<div class="flex-none border-b border-gray-100 p-1.5">
		<h3 class="text-2xs mb-1 font-semibold text-gray-600">Input Types</h3>
		{#if inferredInputTypes.length === 0}
			<div class="text-2xs text-gray-400 italic">Connect a node...</div>
		{:else}
			<div class="space-y-1">
				{#each inferredInputTypes as type (type)}
					{@const color = getColorForType(type.id)}
					<div
						class="text-2xs rounded px-1 py-0.5 font-mono"
						style={`background-color: ${color}20; border-left: 3px solid ${color};`}
					>
						{type.className}
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Display Area for Received Data -->
	<div class="min-h-0 flex-grow overflow-auto p-1.5">
		{#if !receivedData || receivedData.length === 0}
			<div class="text-2xs text-gray-400 italic">Waiting for data...</div>
		{:else}
			<div class="space-y-2">
				{#each receivedData as item, index (index)}
					<div class="rounded border border-gray-200 bg-gray-50 p-1">
						<pre class="text-2xs font-mono break-words whitespace-pre-wrap">{JSON.stringify(
								item,
								null,
								2
							)}</pre>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Error Display Area (Optional) -->
	{#if data.error}
		<div class="mt-auto flex-none border-t border-red-200 bg-red-50 p-1.5">
			<p class="text-2xs font-semibold text-red-700">Error:</p>
			<p class="text-2xs text-red-600">{@html formatErrorMessage(data.error)}</p>
		</div>
	{/if}
</div>

<style>
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}

	/* Use global styles for handles/resizers if available */
	:global(.resize-handle-output) {
		width: 12px !important;
		height: 12px !important;
		border-radius: 3px !important;
		border: 2px solid var(--color-emerald-200) !important;
		background-color: rgba(219, 112, 147, 0.2) !important;
	}

	:global(.resize-line-output) {
		border-color: var(--color-emerald-200) !important;
		border-width: 2px !important;
	}
</style>
