<script lang="ts">
	import { NodeResizer, type Node } from '@xyflow/svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import HeaderIcon from '$lib/components/HeaderIcon.svelte';
	import { persistNodeDataDebounced } from '$lib/utils/nodeUtils';
	import { tick, onMount } from 'svelte';
	import { useUpdateNodeInternals } from '@xyflow/svelte';

	export interface ToolNodeData {
		name: string;
		description: string | null;
		code: string;
		nodeId: string;
		_lastUpdated?: number; // For forcing re-render via #key
	}

	let { id, data } = $props<{
		id: string;
		data: ToolNodeData;
	}>();

	let toolName = $state(data.name || 'new_tool_function');
	let toolDescription = $state(data.description || '');
	let nodeVersion = $derived(data._lastUpdated || 0);
	let codeContent = $derived(data.code || 'def new_tool_function():\n    pass');

	let editingName = $state(false);
	let tempToolName = $state('');
	let toolNameError = $state('');

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

		toolName = tempToolName;
		data.name = tempToolName;
		persistNodeDataDebounced();
		editingName = false;
		toolNameError = '';
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
	}

	async function handleCollapse() {
		await tick(); // Wait for DOM updates
		updateNodeInternals(id);
	}

	// Ensure data object has all fields, especially on creation
	onMount(() => {
		let updated = false;
		if (data.name === undefined) {
			data.name = 'new_tool_function';
			toolName = 'new_tool_function'; // Ensure $state is also updated
			updated = true;
		}
		if (data.description === undefined) {
			data.description = '';
			toolDescription = ''; // Ensure $state is also updated
			updated = true;
		}
		if (data.code === undefined) {
			data.code = 'def new_tool_function():\n    pass';
			// codeContent is derived, so no direct update needed here for it
			updated = true;
		}
		if (updated) {
			persistNodeDataDebounced();
		}
	});

	// Sync toolName with data.name if data.name changes externally and not editing
	$effect(() => {
		if (!editingName && data.name !== undefined && data.name !== toolName) {
			toolName = data.name;
		}
		if (data.description !== undefined && data.description !== toolDescription) {
			toolDescription = data.description;
		}
	});
</script>

<div
	class="tool-node flex h-full flex-col overflow-auto rounded-md border border-gray-300 bg-white shadow-md"
>
	<NodeResizer minWidth={300} minHeight={250} handleClass="resize-handle-toolnode" />

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
					class="nodrag w-full cursor-text rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-yellow-50 focus:border-yellow-400 focus:ring-1 {toolNameError
						? 'border-red-500 ring-red-500'
						: 'focus:ring-yellow-400'}"
					title="Enter the name of the tool function (alphanumeric, _, -)"
					autofocus
				/>
				{#if toolNameError}
					<div class="nodrag mt-0.5 text-center text-xs text-red-500">{toolNameError}</div>
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
		<textarea
			bind:value={toolDescription}
			oninput={handleDescriptionChange}
			placeholder="Tool description (optional)"
			class="nodrag text-2xs w-full cursor-text rounded border border-gray-200 p-1.5 focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
			rows="2"
			title="Enter a description for the tool"
		></textarea>
	</div>

	<div class="relative flex h-full min-h-0 flex-col p-1.5">
		{#key nodeVersion}
			<EditableCodeSection
				title="Tool Function Code"
				code={codeContent}
				language="python"
				onUpdate={handleCodeUpdate}
				showReset={false}
				onUpdateSize={handleCollapse}
			/>
		{/key}
	</div>
</div>

<style>
	:global(.resize-handle-toolnode) {
		width: 12px !important;
		height: 12px !important;
		border-radius: 3px !important;
		border: 2px solid var(--color-yellow-300) !important; /* Updated color */
		background-color: rgba(234, 179, 8, 0.2) !important; /* Updated color for yellow */
	}

	.text-2xs {
		font-size: 0.65rem; /* 10.4px */
		line-height: 1rem; /* 16px */
	}
</style>
