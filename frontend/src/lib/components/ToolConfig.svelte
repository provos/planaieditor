<script lang="ts">
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import HeaderIcon from '$lib/components/HeaderIcon.svelte';
	import { persistNodeDataDebounced } from '$lib/utils/nodeUtils';
	import { tick, onMount, untrack } from 'svelte';
	import { useUpdateNodeInternals } from '@xyflow/svelte';
	import { backendUrl } from '$lib/utils/backendUrl';
	import { formatErrorMessage, debounce } from '$lib/utils/utils';
	import { selectedInterpreterPath } from '$lib/stores/pythonInterpreterStore.svelte';
	import { toolNamesStore } from '$lib/stores/classNameStore';
	import { get } from 'svelte/store';
	import Spinner from 'phosphor-svelte/lib/Spinner';

	export interface ToolNodeData {
		name: string;
		description: string | null;
		code: string;
		nodeId: string; // Should be populated with the node's id
	}

	let { id, data } = $props<{
		id: string;
		data: ToolNodeData;
	}>();

	let toolName = $state(data.name || 'new_tool_function');
	let toolDescription = $state(data.description || '');
	let codeContent = $derived(data.code || 'def new_tool_function():\n    pass');

	let editingName = $state(false);
	let tempToolName = $state('');
	let toolNameError = $state('');

	// Validation state
	let isValidatingTool = $state(false);
	let toolValidationError = $state<string | null>(null);
	let toolValidationWarnings = $state<string[]>([]);
	let isToolValid = $state<boolean | undefined>(undefined); // undefined: not validated, true/false: validated

	const updateNodeInternals = useUpdateNodeInternals();

	function startEditingName() {
		tempToolName = toolName;
		editingName = true;
		toolNameError = '';
	}

	function submitNameChange() {
		if (tempToolName === toolName) {
			editingName = false;
			toolNameError = '';
			return;
		}

		if (tempToolName.trim() === '') {
			toolNameError = 'Name cannot be empty.';
			return;
		}

		if (!/^[a-zA-Z0-9_-]*$/.test(tempToolName)) {
			toolNameError = 'Invalid name. Use alphanumeric, _, -';
			return;
		}

		// check if the name is already in the store
		if (get(toolNamesStore).has(tempToolName)) {
			toolNameError = 'Name already exists.';
			return;
		}

		// remove old name and add new name
		toolNamesStore.update((names) => {
			names.delete(toolName);
			names.add(tempToolName);
			return names;
		});

		toolName = tempToolName;
		data.name = tempToolName;
		persistNodeDataDebounced();
		editingName = false;
		toolNameError = '';
		// Name changed, trigger validation (debounced)
		debouncedValidateTool();
	}

	function cancelEditingName() {
		editingName = false;
		toolNameError = '';
	}

	function handleNameKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			submitNameChange();
		} else if (event.key === 'Escape') {
			event.preventDefault();
			cancelEditingName();
		}
	}

	function handleDescriptionChange(event: Event) {
		const newDescription = (event.target as HTMLInputElement).value;
		toolDescription = newDescription;
		data.description = newDescription;
		persistNodeDataDebounced();
	}

	function handleCodeUpdate(newCode: string) {
		data.code = newCode;
		persistNodeDataDebounced();
		// Code changed, trigger validation (debounced)
		debouncedValidateTool();
	}

	async function validateTool() {
		if (isValidatingTool || !data.name || !data.code) {
			return;
		}

		isValidatingTool = true;
		toolValidationError = null;
		toolValidationWarnings = [];
		isToolValid = undefined; // Mark as pending

		try {
			const response = await fetch(`${backendUrl}/api/validate-tool`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				// Send a snapshot of data, ensuring nodeId is included.
				// The backend expects { node: { data: ToolNodeData } }
				body: JSON.stringify({ node: { data: { ...data, nodeId: id } } })
			});

			const result = await response.json();

			if (result.success) {
				isToolValid = true;
				toolValidationWarnings = result.warnings || [];
				// Optionally, update data with canonical info from result.tool_data if needed
			} else {
				isToolValid = false;
				toolValidationError = result.error?.message || result.error || 'Unknown validation error';
				// If backend sends fullTraceback or nodeName in error, it could be used here.
			}
		} catch (error) {
			console.error('Error validating tool:', error);
			isToolValid = false;
			toolValidationError = 'Failed to connect to the server for tool validation.';
		} finally {
			isValidatingTool = false;
		}
	}

	const debouncedValidateTool = debounce(validateTool, 1200);

	async function handleCollapse() {
		await tick(); // Wait for DOM updates
		updateNodeInternals(id);
	}

	onMount(() => {
		let updated = false;
		if (data.name === undefined) {
			data.name = 'new_tool_function';
			toolName = 'new_tool_function';
			updated = true;
		}
		if (data.description === undefined) {
			data.description = '';
			toolDescription = '';
			updated = true;
		}
		if (data.code === undefined) {
			data.code = 'def new_tool_function():\n    pass';
			updated = true;
		}
		if (data.nodeId === undefined && id) {
			data.nodeId = id; // Ensure nodeId is set from the prop
			updated = true;
		}

		if (updated) {
			persistNodeDataDebounced();
		}

		// Initial validation on mount if essential data exists
		if (data.name && data.code) {
			validateTool(); // Direct call on mount
		}
	});

	// Effect for interpreter changes
	$effect(() => {
		if (selectedInterpreterPath.value) {
			if (data.name && data.code) {
				untrack(validateTool); // Re-validate immediately
			}
		}
	});
</script>

<div class="flex-none border-b bg-yellow-100 p-1">
	<HeaderIcon workerType={'tool'} />
	{#if editingName}
		<div class="flex flex-col">
			<input
				type="text"
				bind:value={tempToolName}
				onblur={submitNameChange}
				onkeydown={handleNameKeydown}
				placeholder="Tool Name"
				class="w-full cursor-text rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-yellow-50 focus:border-yellow-400 focus:ring-1 {toolNameError
					? 'border-red-500 ring-red-500'
					: 'focus:ring-yellow-400'}"
				title="Enter the name of the tool function (alphanumeric, _, -)"
			/>
			{#if toolNameError}
				<div class="mt-0.5 text-center text-xs text-red-500">{toolNameError}</div>
			{/if}
		</div>
	{:else}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div
			class="nodrag w-full cursor-pointer rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-yellow-50"
			onclick={startEditingName}
			role="button"
			tabindex={0}
			title="Click to edit tool name (alphanumeric, _, -)"
		>
			{toolName}
		</div>
	{/if}
</div>

<div class="flex-none border-b p-1.5">
	<input
		type="text"
		bind:value={toolDescription}
		oninput={handleDescriptionChange}
		placeholder="Tool description (optional, single line)"
		class="nodrag text-2xs w-full cursor-text rounded border border-gray-200 px-1.5 py-1 focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
		title="Enter a single-line description for the tool"
		onkeydown={(event) => {
			if (event.key === 'Enter' || event.key === 'Escape') {
				(event.target as HTMLInputElement).blur();
			}
		}}
	/>
</div>

<div class="relative flex h-full min-h-0 flex-col p-1.5">
	<EditableCodeSection
		title="Tool Function Code"
		code={codeContent}
		language="python"
		onUpdate={handleCodeUpdate}
		showReset={false}
		onUpdateSize={handleCollapse}
	/>
	<!-- Validation Status Overlay -->
	<div class="absolute bottom-1 right-3 z-10">
		{#if isValidatingTool}
			<div class="rounded-sm bg-white/50 px-1.5 py-1.5">
				<Spinner size={12} class="animate-spin text-blue-500" weight="bold" />
			</div>
		{:else if data.name && data.code && isToolValid !== undefined}
			<p
				class="text-2xs {isToolValid
					? 'text-green-700'
					: 'text-red-700'} rounded-sm bg-white/50 px-1.5 py-1.5"
			>
				{isToolValid ? 'validated' : 'not validated'}
			</p>
		{/if}
	</div>
</div>

<!-- Error and Warnings Display Area -->
{#if !isValidatingTool && (toolValidationError || (isToolValid && toolValidationWarnings.length > 0))}
	{#if toolValidationError && isToolValid === false}
		<div class="mt-auto flex-none border-t border-red-200 bg-red-50 p-1.5">
			<p class="text-2xs font-semibold text-red-700">Error:</p>
			<p class="text-2xs text-red-600">{@html formatErrorMessage(toolValidationError)}</p>
		</div>
	{/if}
	{#if isToolValid && toolValidationWarnings.length > 0}
		<div class="mt-auto flex-none border-t border-yellow-200 bg-yellow-50 p-1.5">
			<p class="text-2xs font-semibold text-yellow-700">Warnings:</p>
			<ul class="text-2xs mt-0.5 list-inside list-disc text-yellow-600">
				{#each toolValidationWarnings as warning}
					<li>{warning}</li>
				{/each}
			</ul>
		</div>
	{/if}
{/if}

<style>
	.text-2xs {
		font-size: 0.65rem; /* 10.4px */
		line-height: 1rem; /* 16px */
	}
</style>
