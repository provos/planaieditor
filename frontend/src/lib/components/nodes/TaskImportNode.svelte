<script lang="ts">
	import { Handle, Position, NodeResizer } from '@xyflow/svelte';
	import TaskNode from './TaskNode.svelte';
	import type { NodeData as TaskNodeData } from './TaskNode.svelte';
	import Spinner from 'phosphor-svelte/lib/Spinner';
	import DownloadSimple from 'phosphor-svelte/lib/DownloadSimple';

	// Interface for this node's specific data
	export interface TaskImportNodeData {
		modulePath: string;
		selectedClassName: string | null;
		nodeId: string; // The node's ID
		error?: string | null; // Error state is now local
		loading?: boolean; // Loading state is now local
	}

	let { id, data } = $props<{
		id: string;
		data: TaskImportNodeData;
	}>();

	// Initialize data if needed
	if (!data.modulePath) data.modulePath = '';
	if (!data.selectedClassName) data.selectedClassName = null;

	// Internal state
	let internalModulePath = $state(data.modulePath);
	let error = $state<string | null>(null);
	let loading = $state(false);
	let localSelectedClassName = $state<string | null>(data.selectedClassName); // Local reactive state
	let availableClasses = $state<string[]>([]); // Local state for classes
	let taskFields = $state<TaskNodeData['fields']>([]); // Local state for fields

	// Placeholder functions for backend interaction
	async function fetchTaskClasses() {
		loading = true;
		error = null;
		console.log(`Fetching classes for module: ${internalModulePath}...`);
		try {
			// Simulating API call
			// await new Promise(resolve => setTimeout(resolve, 1000));
			// Replace with actual fetch:
			const response = await fetch('http://localhost:5001/api/import-task-classes', {
				// Use actual endpoint
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ module_path: internalModulePath })
			});
			const result = await response.json();
			if (response.ok && result.success) {
				// Check response.ok too
				availableClasses = result.classes; // Update local state
				data.modulePath = internalModulePath; // Update data prop
			} else {
				error = result.error || `HTTP error ${response.status}`;
				availableClasses = []; // Clear local state on error
			}

			// --- Mock Data ---
			// data.availableClasses = ['ImportedTaskA', 'ImportedTaskB'];
			// data.modulePath = internalModulePath;
			// data.selectedClassName = null;
			// data.taskFields = [];
			// --- End Mock Data ---
		} catch (err: any) {
			error = err.message || 'Failed to fetch task classes.';
		} finally {
			loading = false;
		}
	}

	async function fetchTaskFields(className: string) {
		console.log('[fetchTaskFields] Started for class:', className);
		if (!className) return;
		loading = true;
		error = null; // Assign null instead of undefined
		console.log(`Fetching fields for class: ${className} in module ${data.modulePath}...`);
		// TODO: Implement API call to backend /api/get-task-fields
		try {
			// Simulating API call
			// await new Promise(resolve => setTimeout(resolve, 1000));
			// Replace with actual fetch:
			const response = await fetch('http://localhost:5001/api/get-task-fields', {
				// Use actual endpoint
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ module_path: data.modulePath, class_name: className })
			});
			const result = await response.json();
			console.log('[fetchTaskFields] API Result:', result);
			if (response.ok && result.success) {
				// Check response.ok too
				taskFields = result.fields; // Update local state
				console.log('[fetchTaskFields] Success, updating taskFields.');
			} else {
				console.error(
					'[fetchTaskFields] API Error or non-success:',
					result.error || `HTTP ${response.status}`
				);
				error = result.error || `HTTP error ${response.status}`;
				taskFields = []; // Clear local state on error
			}

			// --- Mock Data ---
			// if (className === 'ImportedTaskA') {
			//     data.taskFields = [
			//         { name: 'id', type: 'string', isList: false, required: true, description: 'Unique ID' },
			//         { name: 'value', type: 'float', isList: false, required: false, description: 'Optional value' }
			//     ];
			// } else {
			//      data.taskFields = [
			//         { name: 'name', type: 'string', isList: false, required: true },
			//         { name: 'items', type: 'integer', isList: true, required: true, description: 'List of items' }
			//     ];
			// }
			// data.selectedClassName = className;
			// --- End Mock Data ---
		} catch (err: any) {
			console.error('[fetchTaskFields] Catch block error:', err);
			error = err.message || 'Failed to fetch task fields.';
		} finally {
			console.log('[fetchTaskFields] Setting loading to false.');
			loading = false;
		}
	}

	// Effect 2: Sync local changes UP to prop & trigger fetch
	$effect(() => {
		const currentLocalSelection = localSelectedClassName; // Capture current value
		console.log('[Effect 2] Triggered. currentLocalSelection:', currentLocalSelection);

		// Sync local state change UP to the data prop if they differ
		if (data.selectedClassName !== currentLocalSelection) {
			console.log(
				'[Effect 2] Updating data.selectedClassName from:',
				data.selectedClassName,
				'to:',
				currentLocalSelection
			);
			data.selectedClassName = currentLocalSelection;
		}

		// Fetch fields based on the current local state
		if (currentLocalSelection) {
			console.log('[Effect 2] Calling fetchTaskFields with:', currentLocalSelection);
			fetchTaskFields(currentLocalSelection);
		}
	});

	// Create data structure needed for the embedded TaskNode (read-only view)
	// Use $derived for reactive computation based on other state
	let taskNodeViewData: TaskNodeData = $derived({
		className: localSelectedClassName || 'Select Class',
		fields: taskFields || [],
		nodeId: data.nodeId + '-view',
		error: undefined // Explicitly include optional property
	});
</script>

<div
	class="task-import-node flex h-full flex-col rounded-md border border-gray-300 bg-white shadow-md"
>
	<NodeResizer minWidth={250} minHeight={200} />

	<!-- Header Section -->
	<div class="flex-none border-b border-gray-200 bg-gray-50 p-1.5">
		<div class="mb-1 text-center text-xs font-medium text-gray-700">Import Task from Module</div>
		<div class="flex items-center gap-1">
			<input
				type="text"
				bind:value={internalModulePath}
				placeholder="e.g., my_tasks.core_types"
				class="text-2xs w-full flex-grow rounded border border-gray-200 px-1.5 py-1 {error &&
				!availableClasses.length
					? 'border-red-400'
					: ''}"
				disabled={loading}
			/>
			<button
				class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50"
				onclick={fetchTaskClasses}
				disabled={!internalModulePath || loading}
				title="Load classes from module"
			>
				{#if loading && !localSelectedClassName}
					<Spinner size={12} class="animate-spin" />
				{:else}
					<DownloadSimple size={12} weight="bold" />
				{/if}
			</button>
		</div>
		{#if availableClasses.length > 0}
			<div class="mt-1.5">
				<select
					value={localSelectedClassName}
					onchange={(e) => {
						const target = e.currentTarget as HTMLSelectElement;
						localSelectedClassName = target.value ? target.value : null;
						console.log(
							'[Select onchange] Updated localSelectedClassName:',
							localSelectedClassName
						);
					}}
					class="text-2xs w-full rounded border border-gray-200 px-1.5 py-1"
					disabled={loading}
				>
					<option value={null} disabled selected={!localSelectedClassName}
						>Select a Task Class...</option
					>
					{#each availableClasses as className}
						<option value={className}>{className}</option>
					{/each}
				</select>
			</div>
		{/if}
	</div>

	<!-- Embedded TaskNode for Read-Only View -->
	<div class="relative h-full min-h-0 flex-grow overflow-hidden p-0">
		{#if localSelectedClassName}
			<TaskNode id={taskNodeViewData.nodeId} data={taskNodeViewData} readOnly={true} />
		{:else if !error}
			<div class="text-2xs flex h-full items-center justify-center p-2 italic text-gray-400">
				Enter a Python module path (e.g., `path.to.your.module`) and click Load.
			</div>
		{/if}
	</div>

	<!-- Loading Indicator for Field Fetch -->
	{#if loading && localSelectedClassName}
		<div class="absolute inset-0 z-10 flex items-center justify-center bg-white/70">
			<Spinner size={24} class="animate-spin text-blue-500" />
		</div>
	{/if}

	<!-- Error Display Area -->
	{#if error}
		<div class="mt-auto flex-none border-t border-red-200 bg-red-50 p-1.5">
			<p class="text-2xs font-semibold text-red-700">Error:</p>
			<p class="text-2xs text-red-600">{error}</p>
		</div>
	{/if}
</div>

<style>
	.text-2xs {
		font-size: 0.65rem; /* 10.4px */
		line-height: 1rem; /* 16px */
	}
</style>
