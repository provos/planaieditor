<script lang="ts">
	import { Handle, Position, NodeResizer, useStore, useUpdateNodeInternals } from '@xyflow/svelte';
	import type { Node } from '@xyflow/svelte';
	import { isValidPythonClassName } from '$lib/utils/validation';
	import { getColorForType, calculateHandlePosition } from '$lib/utils/colorUtils';
	import { taskClassNamesStore } from '$lib/stores/classNameStore.svelte';
	import HeaderIcon from '../HeaderIcon.svelte';
	import EditableCodeSection from '../EditableCodeSection.svelte';
	import InputHandle from '../InputHandle.svelte';
	import Trash from 'phosphor-svelte/lib/Trash';
	import PencilSimple from 'phosphor-svelte/lib/PencilSimple';
	import Archive from 'phosphor-svelte/lib/Archive';
	import CaretUp from 'phosphor-svelte/lib/CaretUp';
	import CaretDown from 'phosphor-svelte/lib/CaretDown';
	import { Toggle } from 'bits-ui';
	import type { Snippet } from 'svelte';
	import { tick, untrack } from 'svelte';
	import { formatErrorMessage } from '$lib/utils/utils';
	import { persistNodeDataDebounced } from '$lib/utils/nodeUtils';
	import { onMount } from 'svelte';
	import { openFullScreenEditor } from '$lib/stores/fullScreenEditorStore.svelte';
	import { getTaskByName } from '$lib/stores/taskStore.svelte';
	import { getTaskImportByName } from '$lib/stores/taskImportStore.svelte';
	import TaskConfig from '../TaskConfig.svelte';

	// Base interface for worker node data
	export interface BaseWorkerData {
		workerName: string;
		variableName?: string;
		nodeId: string;
		inputTypes: string[];
		output_types: string[]; // we are exporting this back to python and are using python naming convention
		requiredMembers?: string[];
		isCached?: boolean;
		methods?: Record<string, string>;
		otherMembersSource?: string;
		classVars?: Record<string, any>;
		entryPoint?: boolean;
		_lastUpdated?: number;
		// Derived components can extend this
		[key: string]: any;
	}

	let {
		id,
		data = $bindable<BaseWorkerData>(),
		children,
		additionalOutputType,
		additionalClassStyle,
		minWidth = 250,
		minHeight = 200,
		defaultName = 'BaseWorker',
		isEditable = true
	} = $props<{
		id: string;
		data: BaseWorkerData;
		children?: Snippet;
		additionalOutputType?: string;
		additionalClassStyle?: string;
		minWidth?: number;
		minHeight?: number;
		defaultName?: string;
		isEditable?: boolean;
	}>();

	// Access the SvelteFlow store and internals update hook
	const store = useStore();
	const updateNodeInternals = useUpdateNodeInternals();

	if (!data.inputTypes) {
		data.inputTypes = [];
		persistNodeDataDebounced();
	}

	// --- State Variables ---
	let nodeVersion = $derived(data._lastUpdated || 0);
	let editingWorkerName = $state(false);
	let nameError = $state('');
	let tempWorkerName = $state(data.workerName || defaultName);
	let editingOutputType = $state<number | null>(null);
	let tempType = $state('');
	let typeError = $state('');
	let availableTaskClasses = $state<string[]>([]);
	let inferredInputTypes = $derived<string[]>(data.inputTypes);
	let taskNodeVisibility = $state<Record<string, boolean>>({});
	let manuallySelectedInputType = $derived<string>(
		data.inputTypes.length > 0 ? data.inputTypes[0] : ''
	);
	let currentOutputTypes = $derived<string[]>([...(data.output_types || [])]);
	let currentHeight = $state(minHeight); // State for reactive height
	let localIsCached = $state(data.isCached ?? false); // Local state for the toggle

	// Define core methods that might have special display logic
	const coreMethods = data.requiredMembers || ['consume_work', 'prompt', 'system_prompt'];
	let availableMethods = $derived(Object.keys(data.methods || {}));
	let customMethods = $derived(availableMethods.filter((m) => !coreMethods.includes(m)));
	let otherMembersSource = $derived(data?.otherMembersSource ?? undefined);

	let combinedOutputTypes = $derived(
		currentOutputTypes.length > 0
			? currentOutputTypes
			: additionalOutputType
				? [additionalOutputType]
				: []
	);
	// svelte-ignore non_reactive_update
	let workerType: string | undefined = undefined;
	store.nodes.subscribe((values: Node[]) => {
		const node = values.find((n) => n.id === id);
		if (node) {
			workerType = node.type;
		}
	})();
	const allowedCacheTypes = ['taskworker', 'llmtaskworker', 'chattaskworker'];
	const showCachedOption = workerType && allowedCacheTypes.includes(workerType);

	let inputTypeNodes = $state<Node[]>([]);
	let outputTypeNodes = $state<Node[]>([]);

	// --- Effects for Reactivity ---
	onMount(() => {
		if (!isEditable) {
			return;
		}

		// Subscribe to nodes store changes
		const unsubNodes = store.nodes.subscribe((nodesValue: Node[]) => {
			const currentNodes = nodesValue || [];
			// Find this node and update height
			const thisNode = currentNodes.find((n) => n.id === id);
			if (thisNode) {
				currentHeight = thisNode.measured?.height ?? thisNode.height ?? minHeight;
			}

			computeInputOutputTypes();
			computeOutputTypeNodes();
		});

		// Cleanup function
		return () => {
			unsubNodes();
		};
	});

	// Watch for task class names
	$effect(() => {
		availableTaskClasses = Array.from(taskClassNamesStore);
	});

	function computeInputOutputTypes() {
		store.nodes.subscribe((nodes) => {
			inputTypeNodes = nodes.filter(
				(n) =>
					(n.type === 'task' || n.type === 'taskimport') &&
					n.data?.className &&
					inferredInputTypes.includes((n.data as unknown as NodeData).className)
			);
		})();
	}

	function computeOutputTypeNodes() {
		store.nodes.subscribe((nodes) => {
			outputTypeNodes = nodes.filter(
				(n) =>
					(n.type === 'task' || n.type === 'taskimport') &&
					n.data?.className &&
					combinedOutputTypes.includes((n.data as unknown as NodeData).className)
			);
		})();
	}

	if (isEditable) {
		// Effect to sync localIsCached back to data.isCached
		$effect(() => {
			if (data.isCached !== localIsCached) {
				data.isCached = localIsCached;
				persistNodeDataDebounced();
			}
		});

		// Effect to recompute input/output types when combinedOutputTypes changes
		$effect(() => {
			if (combinedOutputTypes.length > 0) {
				untrack(() => {
					computeOutputTypeNodes();
				});
			}
		});
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
		if (data.workerName !== tempWorkerName) {
			data.workerName = tempWorkerName;
			persistNodeDataDebounced();
		}
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
		persistNodeDataDebounced();
		cancelTypeEditing();
	}

	function deleteOutputType(index: number) {
		let tmpOutputTypes = [...data.output_types];
		tmpOutputTypes = tmpOutputTypes.filter((_: string, i: number) => i !== index);
		data.output_types = tmpOutputTypes;
		currentOutputTypes = tmpOutputTypes;
		persistNodeDataDebounced();
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
		computeInputOutputTypes();
		persistNodeDataDebounced();
	}

	function addOutputTypeFromSelect(event: Event) {
		const select = event.target as HTMLSelectElement;
		if (select && select.value) {
			const newType = select.value;
			if (!data.output_types.includes(newType)) {
				data.output_types = [...data.output_types, newType];
				currentOutputTypes = [...data.output_types];
				persistNodeDataDebounced();
			}
			select.value = ''; // Reset select
		}
	}

	// Handler for code updates
	function handleOtherMembersSourceUpdate(newCode: string | undefined) {
		if (newCode === undefined) {
			delete data.otherMembersSource;
			otherMembersSource = undefined;
		} else {
			data.otherMembersSource = newCode;
			otherMembersSource = newCode;
		}
		persistNodeDataDebounced();
		tick().then(() => {
			updateNodeInternals(id);
		});
	}

	function handleMethodUpdate(methodName: string, newCode: string) {
		if (!data.methods) {
			data.methods = {};
		}
		if (newCode === '') {
			delete data.methods[methodName];
			customMethods = customMethods.filter((m) => m !== methodName);
		} else {
			data.methods[methodName] = newCode;
		}
		persistNodeDataDebounced();
		tick().then(() => {
			updateNodeInternals(id);
		});
	}

	async function toggleTaskNodeVisibility(type: string) {
		taskNodeVisibility[type] = !taskNodeVisibility[type];
		await tick();
		updateNodeInternals(id);
	}

	async function handleCollapse() {
		await tick();
		updateNodeInternals(id);
	}

	function updateInferredInputTypes(updatedInputTypes: string[]) {
		inferredInputTypes = updatedInputTypes;
		persistNodeDataDebounced();
		computeInputOutputTypes();
	}

	function handleFullScreen() {
		openFullScreenEditor(id, 'python');
	}
</script>

<div
	class="base-worker-node relative flex h-full flex-col rounded-md border border-gray-300 bg-white shadow-md {additionalClassStyle}"
>
	<NodeResizer
		{minWidth}
		{minHeight}
		handleClass="resize-handle-custom"
		lineClass="resize-line-custom"
	/>

	<!-- Input Handle (Single for now) -->
	<InputHandle
		{id}
		{data}
		{manuallySelectedInputType}
		{isEditable}
		onUpdate={updateInferredInputTypes}
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
		<HeaderIcon workerType={workerType || 'default'} />
		{#if showCachedOption}
			<div class="absolute top-1 right-1 z-10 flex items-center justify-between">
				{#if localIsCached}
					<span
						class="text-2xs rounded bg-yellow-400 px-1 py-0.5 font-bold text-yellow-900 shadow-sm"
						>CACHED</span
					>
				{:else}
					<span class="text-2xs rounded bg-gray-400/20 px-1 py-0.5 text-gray-900/20 shadow-sm"
						>NOT CACHED</span
					>
				{/if}
				<!-- Cache Toggle -->
				{#if isEditable}
					<Toggle.Root
						aria-label="Toggle cached state"
						class="hover:bg-muted active:bg-dark-10 ml-0.5 h-4 w-4 rounded transition-all data-[state=off]:text-gray-400 data-[state=on]:text-yellow-700"
						bind:pressed={localIsCached}
						title={localIsCached ? 'Worker is Cached' : 'Worker is Not Cached'}
					>
						<Archive size={10} weight="bold" />
					</Toggle.Root>
				{/if}
			</div>
		{/if}
		{#if editingWorkerName}
			<!-- Worker Name Edit Input -->
			<div class="flex flex-col">
				<input
					type="text"
					bind:value={tempWorkerName}
					onblur={updateWorkerName}
					onkeydown={handleNameKeydown}
					class="z-10 w-full rounded border border-gray-200 bg-white px-1.5 py-0.5 text-xs font-medium {nameError
						? 'border-red-500'
						: ''}"
				/>
				{#if nameError}
					<div class="mt-0.5 text-xs text-red-500">{nameError}</div>
				{/if}
			</div>
		{:else}
			<!-- Worker Name Display -->
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<div
				class="z-10 w-full cursor-pointer rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-gray-100"
				onclick={startEditingName}
				role="button"
				tabindex="0"
			>
				{data.workerName || defaultName}
			</div>
		{/if}
	</div>

	<!-- Main Content Area -->
	<div class="flex flex-col overflow-auto p-1.5">
		<!-- Input Types -->
		<div class="mb-2 flex-none">
			<h3 class="text-2xs font-semibold text-gray-600">Input Types (Auto)</h3>
			{#if inferredInputTypes.length === 0}
				<!-- Input Type Select Dropdown (only shown when no edges are connected) -->
				{#if availableTaskClasses.length > 0}
					<div class="mt-1 mb-1">
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
					<div class="text-2xs py-0.5 text-gray-400 italic">Create Task nodes</div>
				{/if}
			{/if}
			<div class="mt-1 space-y-1">
				{#each inferredInputTypes as type (type)}
					{@const color = getColorForType(type)}
					{@const taskItem = getTaskByName(type) || getTaskImportByName(type)}
					<div
						class="text-2xs group flex items-center justify-between rounded px-1 py-0.5"
						style={`background-color: ${color}20; border-left: 3px solid ${color};`}
					>
						<div
							class="flex flex-grow cursor-pointer items-center"
							onclick={() => taskItem && toggleTaskNodeVisibility(type)}
							role="button"
							tabindex={taskItem ? 0 : -1}
							onkeypress={(e) => {
								if (taskItem && (e.key === 'Enter' || e.key === ' '))
									toggleTaskNodeVisibility(type);
							}}
							title={taskItem
								? taskNodeVisibility[type]
									? `Collapse details for ${type}`
									: `Expand details for ${type}`
								: type}
						>
							<span class="font-mono">{type}</span>
							{#if taskItem}
								{#if taskNodeVisibility[type]}
									<CaretUp size={10} class="ml-1 text-gray-500 group-hover:text-gray-700" />
								{:else}
									<CaretDown size={10} class="ml-1 text-gray-500 group-hover:text-gray-700" />
								{/if}
							{/if}
						</div>
						{#if manuallySelectedInputType === type && isEditable}
							<!-- Delete button for manually selected input type -->
							<button
								class="ml-1 flex h-3 w-3 flex-shrink-0 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity duration-150 ease-in-out group-hover:opacity-100 hover:bg-red-50 hover:text-red-500"
								onclick={(e) => {
									e.stopPropagation(); // Prevent toggle when deleting
									resetManualInputType();
								}}
								title="Remove manual input type"
							>
								<Trash size={8} weight="bold" />
							</button>
						{/if}
					</div>
					{#if taskItem && taskNodeVisibility[type]}
						<div class="mt-0.5 ml-2 border-l-2 border-gray-200 pl-2">
							<TaskConfig
								id={taskItem.id}
								showAsNode={false}
								allowEditing={false}
								styleClasses="p-0"
							/>
						</div>
					{/if}
				{/each}
			</div>
		</div>

		<!-- Output Types -->
		<div class="mb-2 flex-none">
			<h3 class="text-2xs mb-1 font-semibold text-gray-600">Output Types</h3>
			{#if availableTaskClasses.length > 0}
				<div class="mb-1">
					{#if isEditable}
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
				<div class="text-2xs py-0.5 text-gray-400 italic">No output types defined</div>
			{/if}
			<div class="mt-1 space-y-1">
				{#each currentOutputTypes as type, index (type)}
					{@const color = getColorForType(type)}
					{@const node = outputTypeNodes.find(
						(n) => (n.data as unknown as NodeData).className === type
					)}
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
							<div
								class="flex flex-grow cursor-pointer items-center"
								onclick={() => node && toggleTaskNodeVisibility(type)}
								role="button"
								tabindex={node ? 0 : -1}
								onkeypress={(e) => {
									if (node && (e.key === 'Enter' || e.key === ' ')) toggleTaskNodeVisibility(type);
								}}
								title={node
									? taskNodeVisibility[type]
										? `Collapse details for ${type}`
										: `Expand details for ${type}`
									: type}
							>
								<span class="font-mono">{type}</span>
								{#if node}
									{#if taskNodeVisibility[type]}
										<CaretUp size={10} class="ml-1 text-gray-500 group-hover:text-gray-700" />
									{:else}
										<CaretDown size={10} class="ml-1 text-gray-500 group-hover:text-gray-700" />
									{/if}
								{/if}
							</div>
							{#if isEditable}
								<div class="flex">
									<button
										class="ml-1 flex h-3 w-3 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-gray-200 hover:text-blue-500"
										onclick={(e) => {
											e.stopPropagation(); // Prevent toggle when editing
											startEditingOutputType(index);
										}}
										title="Edit type"><PencilSimple size={8} weight="bold" /></button
									>
									<button
										class="ml-1 flex h-3 w-3 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-50 hover:text-red-500"
										onclick={(e) => {
											e.stopPropagation(); // Prevent toggle when deleting
											deleteOutputType(index);
										}}
										title="Remove type"><Trash size={8} weight="bold" /></button
									>
								</div>
							{/if}
						</div>
						{#if node && taskNodeVisibility[type]}
							<div class="mt-0.5 ml-2 border-l-2 border-gray-200 pl-2">
								<TaskNode
									id={node.id}
									data={node.data as unknown as NodeData}
									showAsNode={false}
									allowEditing={false}
									styleClasses="p-0"
								/>
							</div>
						{/if}
					{/if}
				{/each}
			</div>
		</div>

		<!-- Other Members Section -->
		{#if otherMembersSource !== undefined}
			<div class="mt-3 flex-none border-t border-gray-200 p-1.5">
				<h3 class="text-2xs mb-1 font-semibold text-gray-600">Other Class Members</h3>
				{#key nodeVersion}
					<EditableCodeSection
						title="Custom Code"
						code={data.otherMembersSource}
						language="python"
						showReset={true}
						onReset={() => handleOtherMembersSourceUpdate(undefined)}
						onUpdate={handleOtherMembersSourceUpdate}
						onUpdateSize={handleCollapse}
						onFullScreen={handleFullScreen}
					/>
				{/key}
			</div>
		{/if}

		<!-- Content Area - Modified to allow editor growth -->
		<div class="flex-auto">
			<!-- Placeholder for derived component content -->
			<div>
				{@render children?.()}
			</div>

			<!-- Custom Methods -->
			{#if customMethods.length > 0}
				<div class="mt-3 border-t border-gray-200 pt-1.5">
					<h4 class="text-2xs mb-1 font-medium text-gray-500">Custom Methods</h4>
					{#each customMethods as methodName (methodName)}
						{#key nodeVersion}
							<EditableCodeSection
								title={methodName}
								initialCollapsed={true}
								code={data.methods[methodName]}
								showReset={true}
								onReset={() => handleMethodUpdate(methodName, '')}
								language="python"
								onUpdate={(newCode) => handleMethodUpdate(methodName, newCode)}
								onUpdateSize={handleCollapse}
								onFullScreen={handleFullScreen}
							/>
						{/key}
					{/each}
				</div>
			{/if}
		</div>

		<!-- Error Display Area -->
		{#if data.error}
			<div class="mt-auto flex-none border-t border-red-200 bg-red-50 p-1.5">
				<p class="text-2xs font-semibold text-red-700">Error:</p>
				<p class="text-2xs text-red-600">{@html formatErrorMessage(data.error)}</p>
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
