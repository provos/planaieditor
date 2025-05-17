<script lang="ts">
	import { tick } from 'svelte';
	import { useUpdateNodeInternals, useStore } from '@xyflow/svelte';
	import { persistNodeDataDebounced } from '$lib/utils/nodeUtils';
	import { backendUrl } from '$lib/utils/backendUrl';
	import TaskNode from './TaskNode.svelte';
	import type { NodeData as TaskNodeData } from './TaskNode.svelte';
	import Spinner from 'phosphor-svelte/lib/Spinner';
	import DownloadSimple from 'phosphor-svelte/lib/DownloadSimple';
	import MagicWand from 'phosphor-svelte/lib/MagicWand';
	import { onMount } from 'svelte';
	import { selectedInterpreterPath } from '$lib/stores/pythonInterpreterStore.svelte'; // Import the store

	// Interface for this node's specific data
	export interface TaskImportNodeData extends TaskNodeData {
		modulePath?: string;
		isImplicit?: boolean;
		availableClasses?: string[];
	}

	let { id, data } = $props<{
		id: string;
		data: TaskImportNodeData;
	}>();

	const { edges } = useStore();

	// Initialize data if needed
	if (!data.modulePath) {
		data.modulePath = '';
		persistNodeDataDebounced();
	}
	if (!data.className) {
		data.className = null;
		persistNodeDataDebounced();
	}

	const updateNodeInternals = useUpdateNodeInternals();

	// Internal state
	let internalModulePath = $state(data.modulePath);
	let error = $state<string | null>(null);
	let loading = $state(false);
	let localSelectedClassName = $state<string | null>(data.className); // Local reactive state
	let availableClasses = $state<string[]>(data.availableClasses || []); // Local state for classes
	let hasFetchedFields = $state(false); // Track if fields have been fetched for the current class

	if (!data.fields) {
		data.fields = [];
		persistNodeDataDebounced();
	}

	let dataCopy = $state(data);

	// Placeholder functions for backend interaction
	async function fetchTaskClasses() {
		loading = true;
		error = null;
		console.log(`Fetching classes for module: ${internalModulePath}...`);
		try {
			// Simulating API call
			// await new Promise(resolve => setTimeout(resolve, 1000));
			// Replace with actual fetch:
			const response = await fetch(`${backendUrl}/api/import-task-classes`, {
				// Use actual endpoint
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ module_path: internalModulePath })
			});
			const result = await response.json();
			if (response.ok && result.success) {
				// Check response.ok too
				availableClasses = result.classes; // Update local state
				data.availableClasses = result.classes; // Update data prop
				data.modulePath = internalModulePath; // Update data prop
				dataCopy = {
					...dataCopy,
					modulePath: internalModulePath,
					className: null,
					fields: []
				};
			} else {
				error = result.error || `HTTP error ${response.status}`;
				availableClasses = []; // Clear local state on error
				data.availableClasses = []; // Clear data prop on error
			}
			persistNodeDataDebounced();
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
			const response = await fetch(`${backendUrl}/api/get-task-fields`, {
				// Use actual endpoint
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ module_path: data.modulePath, class_name: className })
			});
			const result = await response.json();
			console.log('[fetchTaskFields] API Result:', result);
			if (response.ok && result.success) {
				// Check response.ok too
				data.fields = result.fields;
				persistNodeDataDebounced();
				dataCopy = {
					...dataCopy,
					fields: result.fields
				};
				console.log('[fetchTaskFields] Success, updating fields.');
			} else {
				console.error(
					'[fetchTaskFields] API Error or non-success:',
					result.error || `HTTP ${response.status}`
				);
				error = result.error || `HTTP error ${response.status}`;
				data.fields = [];
				persistNodeDataDebounced();
				dataCopy = {
					...dataCopy,
					fields: []
				};
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
			// data.className = className;
			// --- End Mock Data ---
		} catch (err: any) {
			console.error('[fetchTaskFields] Catch block error:', err);
			error = err.message || 'Failed to fetch task fields.';
		} finally {
			console.log('[fetchTaskFields] Setting loading to false.');
			hasFetchedFields = !error; // Mark as fetched if no error
			loading = false;
		}
	}

	let isEdgeConnected = $state(false);

	// Fetch fields when component mounts AND interpreter is selected AND class is selected
	onMount(() => {
		if (selectedInterpreterPath.value && data.className && !hasFetchedFields) {
			fetchTaskFields(data.className);
		}

		const unsubEdges = edges.subscribe((edges) => {
			isEdgeConnected = edges.some((edge) => edge.source === id);
		});

		return () => {
			unsubEdges();
		};
	});

	// Sync local changes UP to prop & potentially trigger fetch
	$effect(() => {
		if (data.className !== localSelectedClassName) {
			data.className = localSelectedClassName;
			persistNodeDataDebounced();
			dataCopy = {
				...dataCopy,
				className: localSelectedClassName
			};
			hasFetchedFields = false; // Reset fetch status when class changes
			tick().then(() => {
				updateNodeInternals(id);
			});

			// Fetch fields based on the current local state IF interpreter is selected
			if (localSelectedClassName && selectedInterpreterPath.value && !hasFetchedFields) {
				console.log('[Effect 2] Calling fetchTaskFields with:', localSelectedClassName);
				fetchTaskFields(localSelectedClassName);
			}
		}
	});

	// Trigger fetch when interpreter becomes available AND class is already selected
	$effect(() => {
		const currentPath = selectedInterpreterPath.value;
		if (currentPath && localSelectedClassName && !hasFetchedFields) {
			console.log(
				'[Effect 3] Interpreter selected, calling fetchTaskFields with:',
				localSelectedClassName
			);
			fetchTaskFields(localSelectedClassName);
		}
	});
</script>

{#snippet ImportHeader()}
	<!-- Snippet Content: Import Header -->
	<div class="import-controls w-full">
		<div class="text-2xs mb-1 flex items-center justify-center gap-1 text-center text-gray-700">
			{#if data.isImplicit}
				<span>Implicitly Imported Task</span>
				<span title="Implicitly imported Task">
					<MagicWand size={10} weight="duotone" class="text-purple-600" />
				</span>
			{:else}
				<span>Import Task from Module</span>
			{/if}
		</div>
		<div class="flex items-center gap-1">
			<input
				type="text"
				bind:value={internalModulePath}
				placeholder="e.g., my_tasks.core_types"
				class="text-2xs w-full flex-grow rounded border border-gray-200 px-1.5 py-1 disabled:cursor-not-allowed {error &&
				!availableClasses.length
					? 'border-red-400'
					: ''}"
				disabled={loading || data.isImplicit || isEdgeConnected}
			/>
			<button
				class="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded bg-blue-500 text-white hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-blue-500"
				onclick={fetchTaskClasses}
				disabled={!internalModulePath || loading || data.isImplicit || isEdgeConnected}
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
					disabled={loading || !selectedInterpreterPath.value || data.isImplicit || isEdgeConnected}
					title={data.isImplicit
						? 'Cannot change implicitly imported task'
						: !selectedInterpreterPath.value
							? 'Select a Python interpreter first'
							: ''}
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

		<!-- Loading Indicator for Field Fetch -->
		{#if loading && localSelectedClassName}
			<div
				class="absolute top-full left-0 z-10 mt-px flex w-full items-center justify-center bg-white/70 py-1"
			>
				<Spinner size={16} class="animate-spin text-blue-500" />
			</div>
		{/if}

		<!-- Error Display Area -->
		{#if error}
			<div class="mt-1.5 border-t border-red-200 bg-red-50 p-1.5">
				<p class="text-2xs font-semibold text-red-700">Error:</p>
				<p class="text-2xs text-red-600">{error}</p>
			</div>
		{/if}
	</div>
{/snippet}

<TaskNode {id} data={dataCopy} allowEditing={false}>
	{@render ImportHeader()}
</TaskNode>

<style>
	/* Ensure child snippet takes full width and specific styling */
	:global(.task-node > div:first-child > .import-controls) {
		padding: 0.375rem; /* p-1.5 */
		width: 100%;
	}
	/* You might need additional styles here or in TaskNode */
	.text-2xs {
		font-size: 0.65rem; /* 10.4px */
		line-height: 1rem; /* 16px */
	}
</style>
