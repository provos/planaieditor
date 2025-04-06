<script lang="ts">
	import { Handle, Position, NodeResizer, useStore } from '@xyflow/svelte';
	import { isValidPythonClassName } from '$lib/utils/validation';
	import { allClassNames } from '$lib/stores/classNameStore';
	import Trash from 'phosphor-svelte/lib/Trash';
	import PencilSimple from 'phosphor-svelte/lib/PencilSimple';
	import type { Node, Edge } from '@xyflow/svelte';
	import type { Snippet } from 'svelte';

	// Base interface for worker node data
	export interface BaseWorkerData {
		workerName: string;
		nodeId: string;
		inputTypes: string[];
		outputTypes: string[];
		// Derived components can extend this
		[key: string]: any;
	}

	let {
		id,
		data,
		children,
		minWidth = 250,
		minHeight = 200,
		defaultName = 'BaseWorker'
	} = $props<{
		id: string;
		data: BaseWorkerData;
		children?: Snippet;
		minWidth?: number;
		minHeight?: number;
		defaultName?: string;
	}>();

	// Access the SvelteFlow store
	const store = useStore();

	// --- State Variables ---
	let editingWorkerName = $state(false);
	let nameError = $state('');
	let tempWorkerName = $state(data.workerName || defaultName);
	let editingOutputType = $state<number | null>(null);
	let tempType = $state('');
	let typeError = $state('');
	let availableTaskClasses = $state<string[]>([]);
	let inferredInputTypes = $state<string[]>([]);
	let currentOutputTypes = $state<string[]>([...(data.outputTypes || [])]);

	// --- Effects for Reactivity ---
	$effect(() => {
		let currentNodes: Node[] = [];
		let currentEdges: Edge[] = [];

		// Subscribe to nodes store changes
		const unsubNodes = store.nodes.subscribe((nodesValue) => {
			currentNodes = nodesValue || [];
			updateInferredTypes(currentNodes, currentEdges);
		});

		// Subscribe to edges store changes
		const unsubEdges = store.edges.subscribe((edgesValue) => {
			currentEdges = edgesValue || [];
			updateInferredTypes(currentNodes, currentEdges);
		});

		// Subscribe to the allClassNames store for output type selection
		const unsubClassNames = allClassNames.subscribe((classMap) => {
			const taskNodeClasses = Array.from(classMap.values());
			availableTaskClasses = taskNodeClasses.filter((cn) => cn !== data.workerName);
		});

		// Initial update in case stores already have values
		updateInferredTypes(currentNodes, currentEdges);

		// Cleanup function
		return () => {
			unsubNodes();
			unsubEdges();
			unsubClassNames();
		};
	});

	// Function to calculate and update inferred input types
	function updateInferredTypes(nodes: Node[], edges: Edge[]) {
		if (!edges || !nodes) {
			inferredInputTypes = [];
			return;
		}

		const incomingEdges = edges.filter((edge: Edge) => edge.target === id);
		const sourceNodeIds = incomingEdges.map((edge: Edge) => edge.source);
		const sourceClassNames: string[] = sourceNodeIds
			.map((nodeId: string) => {
				const sourceNode = nodes.find((node: Node) => node.id === nodeId);
				return sourceNode?.data?.className;
			})
			.filter(Boolean) as string[];

		inferredInputTypes = sourceClassNames;
		data.inputTypes = sourceClassNames;
	}

	// Update local output types when data changes
	$effect(() => {
		currentOutputTypes = [...(data.outputTypes || [])];
	});

	// --- Worker Name Editing Logic ---
	function startEditingName() {
		tempWorkerName = data.workerName || defaultName;
		editingWorkerName = true;
	}

	function validateWorkerName(name: string): boolean {
		if (!isValidPythonClassName(name)) {
			nameError = 'Invalid Python class name';
			return false;
		}
		if (!name.endsWith('Worker')) {
			nameError = 'Worker name must end with "Worker"';
			return false;
		}
		nameError = '';
		return true;
	}

	function updateWorkerName() {
		if (!validateWorkerName(tempWorkerName)) return;
		data.workerName = tempWorkerName;
		editingWorkerName = false;
	}

	function cancelEditingName() {
		tempWorkerName = data.workerName || defaultName;
		nameError = '';
		editingWorkerName = false;
	}

	function handleNameKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') updateWorkerName();
		else if (event.key === 'Escape') cancelEditingName();
	}

	// --- Output Type Handling Logic ---
	function startEditingOutputType(index: number = -1) {
		tempType = index >= 0 ? data.outputTypes[index] : '';
		editingOutputType = index;
		typeError = '';
	}

	function validateType(typeName: string): boolean {
		if (!typeName) {
			typeError = 'Type name is required';
			return false;
		}
		if (!isValidPythonClassName(typeName)) {
			typeError = 'Invalid Python class name';
			return false;
		}
		typeError = '';
		return true;
	}

	function saveOutputType() {
		if (!validateType(tempType)) return;
		if (editingOutputType === -1) {
			data.outputTypes = [...data.outputTypes, tempType];
		} else {
			data.outputTypes = data.outputTypes.map((type: string, i: number) =>
				i === editingOutputType ? tempType : type
			);
		}
		currentOutputTypes = [...data.outputTypes];
		cancelTypeEditing();
	}

	function deleteOutputType(index: number) {
		data.outputTypes = data.outputTypes.filter((_: string, i: number) => i !== index);
		currentOutputTypes = [...data.outputTypes];
	}

	function cancelTypeEditing() {
		editingOutputType = null;
		tempType = '';
		typeError = '';
	}

	function addOutputTypeFromSelect(event: Event) {
		const select = event.target as HTMLSelectElement;
		if (select && select.value) {
			const newType = select.value;
			if (!data.outputTypes.includes(newType)) {
				data.outputTypes = [...data.outputTypes, newType];
				currentOutputTypes = [...data.outputTypes];
			}
			select.value = ''; // Reset select
		}
	}
</script>

<div
	class="base-worker-node flex h-full flex-col rounded-md border border-gray-300 bg-white shadow-md"
>
	<NodeResizer {minWidth} {minHeight} />
	<Handle type="target" position={Position.Left} id="input" />
	<Handle type="source" position={Position.Right} id="output" />

	<!-- Header -->
	<div class="flex-none border-b border-gray-200 bg-gray-50 p-1">
		{#if editingWorkerName}
			<!-- Worker Name Edit Input -->
			<div class="flex flex-col">
				<input
					type="text"
					bind:value={tempWorkerName}
					onblur={updateWorkerName}
					onkeydown={handleNameKeydown}
					class="w-full rounded border border-gray-200 bg-white px-1.5 py-0.5 text-xs font-medium {nameError
						? 'border-red-500'
						: ''}"
					autofocus
				/>
				{#if nameError}
					<div class="mt-0.5 text-xs text-red-500">{nameError}</div>
				{/if}
			</div>
		{:else}
			<!-- Worker Name Display -->
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<div
				class="w-full cursor-pointer rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-gray-100"
				onclick={startEditingName}
				role="button"
				tabindex="0"
			>
				{data.workerName || defaultName}
			</div>
		{/if}
	</div>

	<!-- Main Content Area -->
	<div class="flex h-full min-h-0 flex-col overflow-hidden p-1.5">
		<!-- Input Types -->
		<div class="mb-2 flex-none">
			<h3 class="text-2xs font-semibold text-gray-600">Input Types (Auto)</h3>
			{#if inferredInputTypes.length === 0}
				<div class="text-2xs py-0.5 italic text-gray-400">Connect Task nodes</div>
			{/if}
			<div class="mt-1 space-y-1">
				{#each inferredInputTypes as type}
					<div class="text-2xs flex items-center rounded bg-green-50 px-1 py-0.5">
						<span class="font-mono">{type}</span>
					</div>
				{/each}
			</div>
		</div>

		<!-- Output Types -->
		<div class="mb-2 flex-none">
			<h3 class="text-2xs mb-1 font-semibold text-gray-600">Output Types</h3>
			{#if availableTaskClasses.length > 0}
				<div class="mb-1">
					<select
						class="text-2xs w-full rounded border border-gray-200 px-1 py-0.5"
						onchange={addOutputTypeFromSelect}
					>
						<option value="">Add output type...</option>
						{#each availableTaskClasses as className}
							<option value={className}>{className}</option>
						{/each}
					</select>
				</div>
			{/if}
			{#if currentOutputTypes.length === 0}
				<div class="text-2xs py-0.5 italic text-gray-400">No output types defined</div>
			{/if}
			<div class="mt-1 space-y-1">
				{#each currentOutputTypes as type, index}
					{#if editingOutputType === index}
						<!-- Output Type Edit Form -->
						<div class="rounded border border-blue-200 bg-blue-50 p-1">
							<div class="mb-1">
								<input
									type="text"
									bind:value={tempType}
									onkeydown={handleNameKeydown}
									class="text-2xs w-full rounded border border-gray-200 px-1 py-0.5 {typeError
										? 'border-red-500'
										: ''}"
									autofocus
								/>
								{#if typeError}<div class="text-2xs mt-0.5 text-red-500">{typeError}</div>{/if}
							</div>
							<div class="flex justify-end space-x-1">
								<button
									class="text-2xs rounded bg-gray-200 px-1 py-0.5 hover:bg-gray-300"
									onclick={cancelTypeEditing}>Cancel</button
								>
								<button
									class="text-2xs rounded bg-blue-500 px-1 py-0.5 text-white hover:bg-blue-600"
									onclick={saveOutputType}>Save</button
								>
							</div>
						</div>
					{:else}
						<!-- Output Type Display Item -->
						<div
							class="text-2xs group flex items-center justify-between rounded bg-purple-50 px-1 py-0.5"
						>
							<span class="font-mono">{type}</span>
							<div class="flex">
								<button
									class="ml-1 flex h-3 w-3 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity hover:bg-gray-200 hover:text-blue-500 group-hover:opacity-100"
									onclick={() => startEditingOutputType(index)}
									title="Edit type"><PencilSimple size={8} weight="bold" /></button
								>
								<button
									class="ml-1 flex h-3 w-3 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
									onclick={() => deleteOutputType(index)}
									title="Remove type"><Trash size={8} weight="bold" /></button
								>
							</div>
						</div>
					{/if}
				{/each}
			</div>
		</div>

		<!-- Placeholder for derived component content -->
		<div class="min-h-0 flex-grow">
			{@render children?.()}
		</div>
	</div>
</div>

<style>
	/* Styles for this component */
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
