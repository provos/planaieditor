<script lang="ts">
	import { Handle, Position, NodeResizer, useNodes, type Node } from '@xyflow/svelte';
	import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';
	import { getColorForType } from '$lib/utils/colorUtils';
	import EditableCodeSection from '../EditableCodeSection.svelte';
	import { onDestroy, onMount, untrack, tick } from 'svelte';
	import { useUpdateNodeInternals } from '@xyflow/svelte';
	import { formatErrorMessage, debounce } from '$lib/utils/utils';
	import type { NodeData as TaskNodeData } from './TaskNode.svelte';
	import { backendUrl } from '$lib/utils/backendUrl';
	import Spinner from 'phosphor-svelte/lib/Spinner';
	import HeaderIcon from '../HeaderIcon.svelte';
	import { selectedInterpreterPath } from '$lib/stores/pythonInterpreterStore.svelte';
	import { useStore } from '@xyflow/svelte';
	import { persistNodeDataDebounced } from '$lib/utils/nodeUtils';
	import type { Edge } from '@xyflow/svelte';

	// Define the interface for the node's data
	export interface DataInputNodeData {
		className: string | null; // Can be null initially
		jsonData: string;
		isJsonValid?: boolean;
		nodeId: string;
	}

	// Props passed by SvelteFlow
	let { id, data } = $props<{
		id: string;
		data: DataInputNodeData;
	}>();

	const { nodes, edges } = useStore();

	// Ensure jsonData is initialized
	if (!data.jsonData) {
		data.jsonData = '{}'; // Default to empty JSON object
		persistNodeDataDebounced(id, nodes, data);
	}

	// --- State Variables ---
	let availableTaskClasses = $state<string[]>([]);
	let selectedClassName = $state<string | null>(data.className); // Use state for reactivity
	let errorMessage = $state<string | null>(null);
	let jsonIsValid = $state<boolean>(false);
	let isLoading = $state<boolean>(false);
	let canBeUsedForAssistant = $state<boolean>(false);

	const updateNodeInternals = useUpdateNodeInternals();

	// Subscribe to task class names
	const unsubTaskTypes = taskClassNamesStore.subscribe((taskClasses) => {
		availableTaskClasses = Array.from(taskClasses);
		// If the current className is no longer valid, reset it
		if (selectedClassName && !taskClasses.has(selectedClassName)) {
			selectedClassName = null;
			data.className = null;
			persistNodeDataDebounced(id, nodes, data);
			deleteExistingEdges();
		}
	});

	function deleteExistingEdges() {
		let currentEdges: Edge[] = [];
		edges.subscribe((edges) => {
			currentEdges = edges;
		});
		edges.set(currentEdges.filter((edge) => edge.source !== id));
	}

	async function checkCanBeUsedForAssistant() {
		if (selectedClassName != 'ChatTask') {
			canBeUsedForAssistant = false;
			return;
		}
		canBeUsedForAssistant = true;
	}

	// --- Effects ---
	onMount(() => {
		if (selectedClassName) {
			validateJsonData();
			checkCanBeUsedForAssistant(); // async function does not trigger reactivity
		}
	});

	// Validate the json data when the interpreter path changes
	$effect(() => {
		if (selectedInterpreterPath.value) {
			untrack(() => validateJsonData());
		}
	});

	// Update data when selectedClassName changes
	$effect(() => {
		if (data.className !== selectedClassName) {
			data.className = selectedClassName;
			checkCanBeUsedForAssistant(); // async function does not trigger reactivity
			persistNodeDataDebounced(id, nodes, data);
			deleteExistingEdges();
			if (selectedClassName) {
				validateJsonData();
			}
			tick().then(() => {
				updateNodeInternals(id);
			});
		}
	});

	// Keep track of the json validity
	$effect(() => {
		if (data.isJsonValid !== jsonIsValid) {
			data.isJsonValid = jsonIsValid;
			persistNodeDataDebounced(id, nodes, data);
		}
	});

	// Handler for code updates from EditableCodeSection
	function handleJsonUpdate(newCode: string) {
		if (!selectedClassName) {
			return;
		}

		data.jsonData = newCode;
		persistNodeDataDebounced(id, nodes, data);
		errorMessage = null;
		jsonIsValid = false;
		debounce(validateJsonData, 1000)();
	}

	async function validateJsonData() {
		if (isLoading || !selectedClassName) {
			// Allow one validation at a time
			return;
		}

		isLoading = true;
		try {
			// find the Task Class Node
			let taskClassNode: Node | undefined;
			nodes.subscribe((nodes) => {
				taskClassNode = nodes.find(
					(node) =>
						(node.type === 'task' || node.type === 'taskimport') &&
						(node.data as unknown as TaskNodeData).className === selectedClassName
				);
			})();

			if (!taskClassNode) {
				errorMessage = `No Task Class Node found for ${selectedClassName}`;
				return;
			}

			const response = await fetch(`${backendUrl}/api/validate-pydantic-data`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ node: taskClassNode, jsonData: data.jsonData })
			});
			const result = await response.json();
			jsonIsValid = result.success;
			if (result.success) {
				errorMessage = null;
			} else {
				errorMessage = result.error;
			}
		} catch (error) {
			console.error('Error validating JSON data:', error);
			errorMessage = 'Error validating JSON data';
		} finally {
			isLoading = false;
		}
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
	class="datainput-node flex h-full flex-col overflow-auto rounded-md border border-gray-300 bg-white shadow-md"
>
	<!-- Node Resizer -->
	<NodeResizer
		minWidth={200}
		minHeight={150}
		handleClass={canBeUsedForAssistant
			? 'resize-handle-datainput-assistant'
			: 'resize-handle-datainput'}
		lineClass={canBeUsedForAssistant ? 'resize-line-datainput-assistant' : 'resize-line-datainput'}
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
	<div class="flex-none border-b bg-gray-50 {canBeUsedForAssistant
		? 'bg-purple-100'
		: 'bg-orange-100'} p-1">
		<HeaderIcon workerType={'datainput'} extraText={canBeUsedForAssistant ? '(Assistant Ready)' : ''} />
		<select
			bind:value={selectedClassName}
			class="w-full cursor-pointer rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-gray-100"
			title="Select the output Task type"
		>
			<option value={null}>Select Output Task Type...</option>
			{#each availableTaskClasses as className (className)}
				<option value={className}>{className}</option>
			{/each}
		</select>
	</div>

	<!-- JSON Data Editor -->
	<div class="relative flex h-full min-h-0 flex-col p-1.5">
		<EditableCodeSection
			title="JSON Data"
			code={data.jsonData}
			language="json"
			onUpdate={handleJsonUpdate}
			initialCollapsed={false}
			onUpdateSize={handleCollapse}
		/>
		<div class="absolute bottom-1 right-3 z-10">
			{#if isLoading}
				<div class="rounded-sm bg-white/50 px-1.5 py-1.5">
					<Spinner size={12} class="animate-spin text-blue-500" />
				</div>
			{:else}
				<p
					class="text-2xs {jsonIsValid
						? 'text-green-700'
						: 'text-red-700'} rounded-sm bg-white/50 px-1.5 py-1.5"
				>
					{jsonIsValid ? 'validated' : 'not validated'}
				</p>
			{/if}
		</div>
	</div>

	<!-- Error Display Area (Optional) -->
	{#if errorMessage}
		<div class="mt-auto flex-none border-t border-red-200 bg-red-50 p-1.5">
			<p class="text-2xs font-semibold text-red-700">Error:</p>
			<p class="text-2xs text-red-600">{@html formatErrorMessage(errorMessage)}</p>
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
	:global(.resize-handle-datainput) {
		width: 12px !important;
		height: 12px !important;
		border-radius: 3px !important;
		border: 2px solid var(--color-orange-200) !important;
		background-color: rgba(100, 149, 237, 0.2) !important;
	}

	:global(.resize-line-datainput) {
		border-color: var(--color-orange-200) !important;
		border-width: 2px !important;
	}

	:global(.resize-handle-datainput-assistant) {
		width: 12px !important;
		height: 12px !important;
		border-radius: 3px !important;
		border: 2px solid var(--color-purple-300) !important;
		background-color: rgba(100, 149, 237, 0.2) !important;
	}

	:global(.resize-line-datainput-assistant) {
		border-color: var(--color-purple-300) !important;
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
