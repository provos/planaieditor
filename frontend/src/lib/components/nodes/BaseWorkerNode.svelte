<script lang="ts">
	import { Handle, Position, NodeResizer, useStore, useUpdateNodeInternals } from '@xyflow/svelte';
	import { isValidPythonClassName } from '$lib/utils/validation';
	import { getColorForType, calculateHandlePosition } from '$lib/utils/colorUtils';
	import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';
	import EditableCodeSection from '../EditableCodeSection.svelte';
	import Trash from 'phosphor-svelte/lib/Trash';
	import PencilSimple from 'phosphor-svelte/lib/PencilSimple';
	import type { Node, Edge } from '@xyflow/svelte';
	import type { Snippet } from 'svelte';
	import { tick } from 'svelte';

	// Base interface for worker node data
	export interface BaseWorkerData {
		workerName: string;
		nodeId: string;
		inputTypes: string[];
		output_types: string[]; // we are exporting this back to python and are using python naming convention
		requiredMembers?: string[];
		isCached?: boolean;
		methods?: Record<string, string>;
		otherMembersSource?: string;
		classVars?: Record<string, any>;
		// Derived components can extend this
		[key: string]: any;
	}

	let {
		id,
		data,
		children,
		additionalOutputType,
		minWidth = 250,
		minHeight = 200,
		defaultName = 'BaseWorker',
		isCached,
		outputTypesEditable = true
	} = $props<{
		id: string;
		data: BaseWorkerData;
		children?: Snippet;
		additionalOutputType?: string;
		minWidth?: number;
		minHeight?: number;
		defaultName?: string;
		isCached?: boolean;
		outputTypesEditable?: boolean;
	}>();

	// Access the SvelteFlow store and internals update hook
	const store = useStore();
	const updateNodeInternals = useUpdateNodeInternals();

	// --- State Variables ---
	let editingWorkerName = $state(false);
	let nameError = $state('');
	let tempWorkerName = $state(data.workerName || defaultName);
	let editingOutputType = $state<number | null>(null);
	let tempType = $state('');
	let typeError = $state('');
	let availableTaskClasses = $state<string[]>([]);
	let inferredInputTypes = $derived<string[]>(data.inputTypes);
	let manuallySelectedInputType = $derived<string>(
		data.inputTypes.length > 0 ? data.inputTypes[0] : ''
	);
	let currentOutputTypes = $derived<string[]>([...(data.output_types || [])]);
	let nodeRef: HTMLElement | null = $state(null);
	let currentHeight = $state(minHeight); // State for reactive height

	let combinedOutputTypes = $derived(
		currentOutputTypes.length > 0
			? currentOutputTypes
			: additionalOutputType
				? [additionalOutputType]
				: []
	);

	// --- Effects for Reactivity ---
	$effect(() => {
		let currentNodes: Node[] = [];
		let currentEdges: Edge[] = [];

		// Subscribe to nodes store changes
		const unsubNodes = store.nodes.subscribe((nodesValue: Node[]) => {
			currentNodes = nodesValue || [];
			// Find this node and update height
			const thisNode = currentNodes.find((n) => n.id === id);
			if (thisNode) {
				currentHeight = thisNode.measured?.height ?? thisNode.height ?? minHeight;
			}
			updateInferredTypes(currentNodes, currentEdges);
		});

		// Subscribe to edges store changes
		const unsubEdges = store.edges.subscribe((edgesValue: Edge[]) => {
			currentEdges = edgesValue || [];
			updateInferredTypes(currentNodes, currentEdges);
		});

		// Subscribe to the taskClassNamesStore for output type selection
		const unsubClassNames = taskClassNamesStore.subscribe((taskClasses) => {
			// This now contains only Task classes, not worker classes
			availableTaskClasses = Array.from(taskClasses);
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

	$effect(() => {
		if (manuallySelectedInputType && inferredInputTypes.length === 0) {
			inferredInputTypes = [manuallySelectedInputType];
			data.inputTypes = [manuallySelectedInputType];
		}
	});

	// Function to calculate and update inferred input types
	function updateInferredTypes(nodes: Node[], edges: Edge[]) {
		if (!edges || !nodes) {
			inferredInputTypes = manuallySelectedInputType ? [manuallySelectedInputType] : [];
			return;
		}

		const incomingEdges = edges.filter((edge: Edge) => edge.target === id);
		const sourceNodeIds = incomingEdges.map((edge: Edge) => edge.source);
		const sourceClassNames: string[] = sourceNodeIds
			.map((nodeId: string) => {
				const sourceNode = nodes.find((node: Node) => node.id === nodeId);
				const edge = incomingEdges.find((e) => e.source === nodeId);
				const sourceHandleId = edge?.sourceHandle;
				if (sourceHandleId && sourceHandleId.startsWith('output-')) {
					return sourceHandleId.substring(7);
				}
				// Fallback if handle ID is missing/unexpected
				return sourceNode?.data?.className;
			})
			.filter(Boolean) as string[];

		// make sourceClassNames unique
		const uniqueSourceClassNames = [...new Set(sourceClassNames)];

		inferredInputTypes = uniqueSourceClassNames;
		data.inputTypes = uniqueSourceClassNames;
	}

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
		tempType = index >= 0 ? data.output_types[index] : '';
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
		let tmpOutputTypes = [...data.output_types];
		if (editingOutputType === -1) {
			tmpOutputTypes.push(tempType);
		} else if (editingOutputType !== null) {
			tmpOutputTypes[editingOutputType] = tempType;
		}
		data.output_types = tmpOutputTypes;
		currentOutputTypes = tmpOutputTypes;
		cancelTypeEditing();
	}

	function deleteOutputType(index: number) {
		let tmpOutputTypes = [...data.output_types];
		tmpOutputTypes = tmpOutputTypes.filter((_: string, i: number) => i !== index);
		data.output_types = tmpOutputTypes;
		currentOutputTypes = tmpOutputTypes;
		typeError = '';
	}

	function cancelTypeEditing() {
		editingOutputType = null;
		tempType = '';
		typeError = '';
	}

	// Keydown handler specifically for the output type edit input
	function handleTypeKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			saveOutputType();
		} else if (event.key === 'Escape') {
			cancelTypeEditing();
			// Prevent the event from bubbling up further
			event.stopPropagation();
		}
	}

	function setInputTypeManually(event: Event) {
		const select = event.target as HTMLSelectElement;
		if (select && select.value) {
			manuallySelectedInputType = select.value;
			select.value = ''; // Reset select
		}
	}

	function resetManualInputType() {
		manuallySelectedInputType = '';
		data.inputTypes = [];
		inferredInputTypes = [];
	}

	function addOutputTypeFromSelect(event: Event) {
		const select = event.target as HTMLSelectElement;
		if (select && select.value) {
			const newType = select.value;
			if (!data.output_types.includes(newType)) {
				data.output_types = [...data.output_types, newType];
				currentOutputTypes = [...data.output_types];
			}
			select.value = ''; // Reset select
		}
	}

	// Handler for code updates
	function handleOtherMembersSourceUpdate(newCode: string) {
		data.otherMembersSource = newCode;
	}

	function handleMethodUpdate(methodName: string, newCode: string) {
		if (!data.methods) {
			data.methods = {};
		}
		data.methods[methodName] = newCode;
	}

	// Define core methods that might have special display logic
	const coreMethods = data.requiredMembers || ['consume_work', 'prompt', 'system_prompt'];
	let availableMethods = $derived(Object.keys(data.methods || {}));
	let customMethods = $derived(availableMethods.filter((m) => !coreMethods.includes(m)));

	async function handleCollapse() {
		await tick();
		updateNodeInternals(id);
	}
</script>

<div
	bind:this={nodeRef}
	class="base-worker-node relative flex h-full flex-col rounded-md border border-gray-300 bg-white shadow-md"
>
	<NodeResizer
		{minWidth}
		{minHeight}
		handleClass="resize-handle-custom"
		lineClass="resize-line-custom"
	/>

	<!-- Input Handle (Single for now) -->
	<Handle
		type="target"
		position={Position.Left}
		id="input"
		style={`background-color: ${getColorForType(inferredInputTypes[0])};`}
	/>

	<!-- Output Handles (Dynamically created) -->
	{#each combinedOutputTypes as type, index (type)}
		{@const handleId = `output-${type}`}
		{@const color = getColorForType(type)}
		{@const topPos = calculateHandlePosition(index, combinedOutputTypes.length, currentHeight)}
		<Handle
			type="source"
			position={Position.Right}
			id={handleId}
			style={`background-color: ${color}; top: ${topPos};`}
		/>
	{/each}

	<!-- Header -->
	<div class="flex-none border-b border-gray-200 bg-gray-50 p-1">
		{#if isCached}
			<span
				class="text-2xs absolute right-1 top-1 z-10 rounded bg-yellow-400 px-1 py-0.5 font-bold text-yellow-900 shadow-sm"
				>CACHED</span
			>
		{/if}
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
				<!-- Input Type Select Dropdown (only shown when no edges are connected) -->
				{#if availableTaskClasses.length > 0}
					<div class="mb-1 mt-1">
						<select
							class="text-2xs w-full rounded border border-gray-200 px-1 py-0.5"
							onchange={setInputTypeManually}
						>
							<option value="">Connect Task nodes or set input type manually...</option>
							{#each availableTaskClasses as className}
								<option value={className}>{className}</option>
							{/each}
						</select>
					</div>
				{:else}
					<div class="text-2xs py-0.5 italic text-gray-400">Create Task nodes</div>
				{/if}
			{/if}
			<div class="mt-1 space-y-1">
				{#each inferredInputTypes as type (type)}
					{@const color = getColorForType(type)}
					<div
						class="text-2xs group flex items-center rounded px-1 py-0.5"
						style={`background-color: ${color}20; border-left: 3px solid ${color};`}
					>
						<span class="font-mono">{type}</span>
						{#if manuallySelectedInputType === type}
							<!-- Delete button for manually selected input type -->
							<button
								class="ml-auto flex h-3 w-3 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity duration-150 ease-in-out group-hover:opacity-100"
								onclick={resetManualInputType}
								title="Remove manual input type"
							>
								<Trash size={8} weight="bold" />
							</button>
						{/if}
					</div>
				{/each}
			</div>
		</div>

		<!-- Output Types -->
		<div class="mb-2 flex-none">
			<h3 class="text-2xs mb-1 font-semibold text-gray-600">Output Types</h3>
			{#if availableTaskClasses.length > 0}
				<div class="mb-1">
					{#if outputTypesEditable}
						<select
							class="text-2xs w-full rounded border border-gray-200 px-1 py-0.5"
							onchange={addOutputTypeFromSelect}
						>
							<option value="">Add output type...</option>
							{#each availableTaskClasses as className}
								<option value={className}>{className}</option>
							{/each}
						</select>
					{/if}
				</div>
			{/if}
			{#if currentOutputTypes.length === 0}
				<div class="text-2xs py-0.5 italic text-gray-400">No output types defined</div>
			{/if}
			<div class="mt-1 space-y-1">
				{#each currentOutputTypes as type, index (type)}
					{@const color = getColorForType(type)}
					{#if editingOutputType === index}
						<!-- Output Type Edit Form -->
						<div class="rounded border border-blue-200 bg-blue-50 p-1">
							<div class="mb-1">
								<input
									type="text"
									bind:value={tempType}
									onkeydown={handleTypeKeydown}
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
						<!-- Output Type Display Item - Now with color -->
						<div
							class="text-2xs group flex items-center justify-between rounded px-1 py-0.5"
							style={`background-color: ${color}20; border-left: 3px solid ${color};`}
						>
							<span class="font-mono">{type}</span>
							{#if outputTypesEditable}
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
							{/if}
						</div>
					{/if}
				{/each}
			</div>
		</div>

		<!-- Other Members Section -->
		{#if data.otherMembersSource}
			<div class="mt-3 flex-none border-t border-gray-200 p-1.5">
				<h3 class="text-2xs mb-1 font-semibold text-gray-600">Other Class Members</h3>
				<EditableCodeSection
					title="Custom Code"
					code={data.otherMembersSource}
					language="python"
					onUpdate={handleOtherMembersSourceUpdate}
					onCollapseToggle={handleCollapse}
				/>
			</div>
		{/if}

		<!-- Scrollable Content Area -->
		<div class="min-h-0 flex-grow overflow-auto">
			<!-- Placeholder for derived component content -->
			<div>
				{@render children?.()}
			</div>

			<!-- Custom Methods -->
			{#if customMethods.length > 0}
				<div class="mt-3 border-t border-gray-200 pt-1.5">
					<h4 class="text-2xs mb-1 font-medium text-gray-500">Custom Methods</h4>
					{#each customMethods as methodName (methodName)}
						<EditableCodeSection
							title={methodName}
							initialCollapsed={true}
							code={data.methods[methodName]}
							language="python"
							onUpdate={(newCode) => handleMethodUpdate(methodName, newCode)}
							onCollapseToggle={handleCollapse}
						/>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Error Display Area -->
		{#if data.error}
			<div class="mt-auto flex-none border-t border-red-200 bg-red-50 p-1.5">
				<p class="text-2xs font-semibold text-red-700">Error:</p>
				<p class="text-2xs text-red-600">{data.error}</p>
			</div>
		{/if}
	</div>
</div>

<style>
	/* Styles for this component */
	:global(.text-2xs) {
		font-size: 0.65rem;
		line-height: 1rem;
	}

	/* Make node relative for absolute handle positioning */
	.base-worker-node {
		position: relative;
	}

	/* Override default handle size/shape for better visibility */
	:global(.svelte-flow .svelte-flow__handle) {
		width: 10px; /* Make handles smaller squares */
		height: 10px;
		border-radius: 2px;
		border: 1px solid rgba(0, 0, 0, 0.2);
		/* background-color is set inline */
	}

	/* Adjust horizontal positioning */
	:global(.svelte-flow .svelte-flow__handle-left) {
		left: -5px; /* Center the smaller handle */
	}

	:global(.svelte-flow .svelte-flow__handle-right) {
		right: -5px; /* Center the smaller handle */
	}

	/* Custom classes for NodeResizer passed via props */
	:global(.resize-handle-custom) {
		width: 12px !important; /* Increased size */
		height: 12px !important;
		border-radius: 3px !important; /* Slightly more rounded */
		border: 2px solid cornflowerblue !important; /* Thicker border */
		background-color: rgba(100, 149, 237, 0.2) !important; /* Subtle background */
	}

	:global(.resize-line-custom) {
		border-color: cornflowerblue !important; /* Match handle color */
		border-width: 2px !important; /* Thicker line */
	}
</style>
