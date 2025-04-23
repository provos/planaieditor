<script lang="ts">
	import { Handle, Position, NodeResizer } from '@xyflow/svelte';
	import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';
	import { getColorForType } from '$lib/utils/colorUtils';
	import EditableCodeSection from '../EditableCodeSection.svelte';
	import { onDestroy } from 'svelte';
	import { tick } from 'svelte';
	import { useUpdateNodeInternals } from '@xyflow/svelte';
    import { formatErrorMessage } from '$lib/utils/utils';

	// Define the interface for the node's data
	export interface DataInputNodeData {
		className: string | null; // Can be null initially
		jsonData: string;
		nodeId: string;
		error?: string; // Optional error field
	}

	// Props passed by SvelteFlow
	let { id, data } = $props<{
		id: string;
		data: DataInputNodeData;
	}>();

	// Ensure jsonData is initialized
	if (!data.jsonData) {
		data.jsonData = '{}'; // Default to empty JSON object
	}

	// --- State Variables ---
	let availableTaskClasses = $state<string[]>([]);
	let selectedClassName = $state<string | null>(data.className); // Use state for reactivity
	const updateNodeInternals = useUpdateNodeInternals();

	// --- Effects ---
	// Subscribe to task class names
	const unsubTaskTypes = taskClassNamesStore.subscribe((taskClasses) => {
		availableTaskClasses = Array.from(taskClasses);
		// If the current className is no longer valid, reset it
		if (selectedClassName && !taskClasses.has(selectedClassName)) {
			selectedClassName = null;
			data.className = null;
		}
	});

	// Update data when selectedClassName changes
	$effect(() => {
		data.className = selectedClassName;
	});

	// Handler for code updates from EditableCodeSection
	function handleJsonUpdate(newCode: string) {
		data.jsonData = newCode;
	}

	// Update node internals when collapsed state changes in code section
	async function handleCollapse() {
		await tick();
		updateNodeInternals(id);
	}

	// --- Cleanup ---
	onDestroy(() => {
		unsubTaskTypes();
	});
</script>

<div
	class="datainput-node flex h-full flex-col rounded-md border border-gray-300 bg-white shadow-md"
>
	<!-- Node Resizer -->
	<NodeResizer
		minWidth={200}
		minHeight={150}
		handleClass="resize-handle-custom"
		lineClass="resize-line-custom"
	/>

	<!-- Output Handle -->
	{#if selectedClassName}
		<Handle
			type="source"
			position={Position.Right}
			id={`output-${selectedClassName}`}
			style={`background-color: ${getColorForType(selectedClassName)};`}
		/>
	{/if}

	<!-- Header with Task Type Selector -->
	<div class="flex-none border-b border-gray-200 bg-gray-50 p-1">
		<select
			bind:value={selectedClassName}
			class="text-2xs w-full rounded border border-gray-200 px-1 py-0.5"
			title="Select the output Task type"
		>
			<option value={null}>Select Output Task Type...</option>
			{#each availableTaskClasses as className (className)}
				<option value={className}>{className}</option>
			{/each}
		</select>
	</div>

	<!-- JSON Data Editor -->
	<div class="flex h-full min-h-0 flex-col overflow-hidden p-1.5">
		<EditableCodeSection
			title="JSON Data"
			code={data.jsonData}
			language="json"
			onUpdate={handleJsonUpdate}
			initialCollapsed={false}
			onCollapseToggle={handleCollapse}
		/>
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
	/* Custom styles for this node type if needed */
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}

	/* Use global styles defined elsewhere for handles/resizers if consistent */
	:global(.resize-handle-custom) {
		width: 12px !important;
		height: 12px !important;
		border-radius: 3px !important;
		border: 2px solid cornflowerblue !important;
		background-color: rgba(100, 149, 237, 0.2) !important;
	}

	:global(.resize-line-custom) {
		border-color: cornflowerblue !important;
		border-width: 2px !important;
	}

	/* Adjust handle size if needed */
	:global(.svelte-flow .svelte-flow__handle) {
		width: 10px;
		height: 10px;
		border-radius: 2px;
		border: 1px solid rgba(0, 0, 0, 0.2);
	}

	:global(.svelte-flow .svelte-flow__handle-right) {
		right: -5px;
	}
</style>
