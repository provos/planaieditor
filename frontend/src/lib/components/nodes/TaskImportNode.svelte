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
		availableClasses: string[];
		taskFields: TaskNodeData['fields']; // Reuse TaskNode's field structure
		nodeId: string; // The node's ID
	}

	let { id, data } = $props<{
		id: string;
		data: TaskImportNodeData;
	}>();

	// Initialize data if needed
	if (!data.modulePath) data.modulePath = '';
	if (!data.selectedClassName) data.selectedClassName = null;
	if (!data.availableClasses) data.availableClasses = [];
	if (!data.taskFields) data.taskFields = [];

	// Internal state
	let internalModulePath = $state(data.modulePath);
	let error = $state<string | null>(null);
	let loading = $state(false);

	// Placeholder functions for backend interaction
	async function fetchTaskClasses() {
		loading = true;
		error = null;
		console.log(`Fetching classes for module: ${internalModulePath}...`);
		// TODO: Implement API call to backend /api/import-task-classes
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
				data.availableClasses = result.classes;
				data.modulePath = internalModulePath; // Update data on success
				data.selectedClassName = null; // Reset selection
				data.taskFields = []; // Clear fields
			} else {
				error = result.error || `HTTP error ${response.status}`;
				data.availableClasses = []; // Clear classes on error
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
		if (!className) return;
		loading = true;
		error = undefined;
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
			if (response.ok && result.success) {
				// Check response.ok too
				data.taskFields = result.fields;
				data.selectedClassName = className; // Update data on success
			} else {
				error = result.error || `HTTP error ${response.status}`;
				data.taskFields = []; // Clear fields on error
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
			error = err.message || 'Failed to fetch task fields.';
		} finally {
			loading = false;
		}
	}

	// Reactive effect to fetch fields when className changes
	$effect(() => {
		if (data.selectedClassName) {
			fetchTaskFields(data.selectedClassName);
		}
	});

	// Create data structure needed for the embedded TaskNode (read-only view)
	let taskNodeViewData = $state<TaskNodeData>({
		className: data.selectedClassName || 'Select Class',
		fields: data.taskFields || [],
		nodeId: data.nodeId + '-view',
		error: undefined
	});

	$effect(() => {
		taskNodeViewData.className = data.selectedClassName || 'Select Class';
		taskNodeViewData.fields = data.taskFields || [];
		// nodeId doesn't change, error can be updated if needed
		// taskNodeViewData.error = data.error;
	});
</script>

<div
	class="task-import-node flex h-full flex-col rounded-md border border-gray-300 bg-white shadow-md"
>
	<NodeResizer minWidth={250} minHeight={200} />

	<!-- Output handle (representing the imported Task type) -->
	<Handle type="source" position={Position.Right} id="output" class="task-import-handle" />

	<!-- Header Section -->
	<div class="flex-none border-b border-gray-200 bg-gray-50 p-1.5">
		<div class="mb-1 text-center text-xs font-medium text-gray-700">Import Task from Module</div>
		<div class="flex items-center gap-1">
			<input
				type="text"
				bind:value={internalModulePath}
				placeholder="e.g., my_tasks.core_types"
				class="text-2xs w-full flex-grow rounded border border-gray-200 px-1.5 py-1 {error &&
				!data.availableClasses.length
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
				{#if loading && !data.selectedClassName}
					<Spinner size={12} class="animate-spin" />
				{:else}
					<DownloadSimple size={12} weight="bold" />
				{/if}
			</button>
		</div>
		{#if data.availableClasses.length > 0}
			<div class="mt-1.5">
				<select
					bind:value={data.selectedClassName}
					class="text-2xs w-full rounded border border-gray-200 px-1.5 py-1"
					disabled={loading}
				>
					<option value={null} disabled selected>Select a Task Class...</option>
					{#each data.availableClasses as className}
						<option value={className}>{className}</option>
					{/each}
				</select>
			</div>
		{/if}
	</div>

	<!-- Embedded TaskNode for Read-Only View -->
	<div class="relative h-full min-h-0 flex-grow overflow-hidden p-0">
		{#if data.selectedClassName}
			<TaskNode id={taskNodeViewData.nodeId} data={taskNodeViewData} readOnly={true} />
		{:else if !error}
			<div class="text-2xs flex h-full items-center justify-center p-2 italic text-gray-400">
				Enter a Python module path (e.g., `path.to.your.module`) and click Load.
			</div>
		{/if}
	</div>

	<!-- Loading Indicator for Field Fetch -->
	{#if loading && data.selectedClassName}
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
	/* Add custom styles if needed */
	.task-import-handle {
		/* Style the handle based on whether a task is selected? */
		background-color: #a0aec0; /* Default gray */
	}
	.text-2xs {
		font-size: 0.65rem; /* 10.4px */
		line-height: 1rem; /* 16px */
	}
</style>
