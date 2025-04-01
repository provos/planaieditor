<script lang="ts">
	import { Handle, Position, NodeResizer } from '@xyflow/svelte';
	import { isValidPythonClassName } from '$lib/utils/validation';
	import { allClassNames } from '$lib/stores/classNameStore';
	import Trash from 'phosphor-svelte/lib/Trash';
	import PencilSimple from 'phosphor-svelte/lib/PencilSimple';
	import CodeMirror from 'svelte-codemirror-editor';
	import { markdown } from '@codemirror/lang-markdown';

	interface LLMWorkerData {
		workerName: string;
		nodeId: string;
		inputTypes: string[];
		outputTypes: string[];
		prompt: string;
		systemPrompt: string;
	}

	let { id, data } = $props<{
		id: string;
		data: LLMWorkerData;
	}>();

	// Ensure data fields are initialized
	if (!data.inputTypes) {
		data.inputTypes = [];
	}
	if (!data.outputTypes) {
		data.outputTypes = [];
	}
	if (!data.prompt) {
		data.prompt = '';
	}
	if (!data.systemPrompt) {
		data.systemPrompt = '';
	}

	// State variables
	let editingWorkerName = $state(false);
	let nameError = $state('');
	let tempWorkerName = $state(data.workerName);

	// Type editing states
	let editingOutputType = $state<number | null>(null);
	let tempType = $state('');
	let typeError = $state('');

	// Available task classes for output selection
	let availableTaskClasses = $state<string[]>([]);

	// Track current types for rendering
	let inferredInputTypes = $state<string[]>([]);
	let currentOutputTypes = $state<string[]>([...data.outputTypes]);

	// Subscribe to the allClassNames store for output type selection
	$effect(() => {
		const unsubscribe = allClassNames.subscribe((classMap) => {
			availableTaskClasses = Array.from(classMap.values());
		});

		return unsubscribe;
	});

	function startEditingName() {
		tempWorkerName = data.workerName;
		editingWorkerName = true;
	}

	function validateWorkerName(name: string): boolean {
		// First check if it's a valid Python class name
		if (!isValidPythonClassName(name)) {
			nameError = 'Invalid Python class name';
			return false;
		}

		// Check if it ends with "Worker" or "TaskWorker"
		if (!name.endsWith('Worker')) {
			nameError = 'Worker name must end with "Worker"';
			return false;
		}

		nameError = '';
		return true;
	}

	function updateWorkerName() {
		if (!validateWorkerName(tempWorkerName)) {
			return;
		}
		data.workerName = tempWorkerName;
		editingWorkerName = false;
	}

	function cancelEditingName() {
		tempWorkerName = data.workerName;
		nameError = '';
		editingWorkerName = false;
	}

	// Handle keydown for worker name editing
	function handleNameKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			updateWorkerName();
		} else if (event.key === 'Escape') {
			cancelEditingName();
		}
	}

	// Output type handling
	function startEditingOutputType(index: number = -1) {
		if (index >= 0) {
			tempType = data.outputTypes[index];
		} else {
			tempType = '';
		}
		editingOutputType = index;
		typeError = '';
	}

	function saveOutputType() {
		if (!validateType(tempType)) return;

		if (editingOutputType === -1) {
			// Add new type
			data.outputTypes = [...data.outputTypes, tempType];
		} else {
			// Update existing type
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

	function cancelTypeEditing() {
		editingOutputType = null;
		tempType = '';
		typeError = '';
	}

	// Handle prompt updates from CodeMirror
	function handlePromptUpdate(event: CustomEvent) {
		data.prompt = event.detail;
	}

	// Handle system prompt updates from CodeMirror
	function handleSystemPromptUpdate(event: CustomEvent) {
		data.systemPrompt = event.detail;
	}

	// Add a new output type from the dropdown
	function addOutputType(event: Event) {
		const select = event.target as HTMLSelectElement;
		if (select && select.value) {
			const newType = select.value;

			// Only add if it doesn't already exist
			if (!data.outputTypes.includes(newType)) {
				data.outputTypes = [...data.outputTypes, newType];
				currentOutputTypes = [...data.outputTypes];
			}

			// Reset the select
			select.value = '';
		}
	}

	// Update tracked fields when data changes
	$effect(() => {
		currentOutputTypes = [...data.outputTypes];
	});
</script>

<div class="llmtaskworker-node flex flex-col rounded-md border border-gray-300 bg-white shadow-md">
	<!-- Node Resizer -->
	<NodeResizer minWidth={250} minHeight={250} />

	<!-- Node handles -->
	<Handle type="target" position={Position.Top} id="input" />
	<Handle type="source" position={Position.Bottom} id="output" />

	<!-- Header with editable worker name -->
	<div class="flex-none border-b border-gray-200 bg-gray-50 p-1">
		{#if editingWorkerName}
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
			<div
				class="w-full cursor-pointer rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-gray-100"
				onclick={startEditingName}
				role="button"
				tabindex="0"
			>
				{data.workerName || 'LLMTaskWorker'}
			</div>
		{/if}
	</div>

	<div class="flex h-full flex-col overflow-hidden p-1.5">
		<!-- Input Types Section - Now inferred from connections -->
		<div class="mb-2 flex-none">
			<div class="flex items-center justify-between">
				<h3 class="text-2xs font-semibold text-gray-600">Input Types (Auto)</h3>
			</div>

			{#if inferredInputTypes.length === 0}
				<div class="text-2xs py-0.5 italic text-gray-400">
					Connect Task nodes to infer input types
				</div>
			{/if}

			<div class="mt-1 space-y-1">
				{#each inferredInputTypes as type}
					<div class="text-2xs flex items-center rounded bg-green-50 px-1 py-0.5">
						<span class="font-mono">{type}</span>
					</div>
				{/each}
			</div>
		</div>

		<!-- Output Types Section -->
		<div class="mb-2 flex-none">
			<div class="flex items-center justify-between">
				<h3 class="text-2xs font-semibold text-gray-600">Output Types</h3>
			</div>

			{#if availableTaskClasses.length > 0}
				<div class="mb-2 mt-1">
					<select
						class="text-2xs w-full rounded border border-gray-200 px-1 py-0.5"
						onchange={addOutputType}
					>
						<option value="">Add an output type...</option>
						{#each availableTaskClasses as className}
							<option value={className}>{className}</option>
						{/each}
					</select>
				</div>
			{:else}
				<div class="text-2xs py-0.5 italic text-gray-400">
					Create Task nodes first to select output types
				</div>
			{/if}

			{#if currentOutputTypes.length === 0 && !availableTaskClasses.length}
				<div class="text-2xs py-0.5 italic text-gray-400">No output types</div>
			{/if}

			<div class="mt-1 space-y-1">
				{#each currentOutputTypes as type, index}
					{#if editingOutputType === index}
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
								{#if typeError}
									<div class="text-2xs mt-0.5 text-red-500">{typeError}</div>
								{/if}
							</div>
							<div class="flex justify-end space-x-1">
								<button
									class="text-2xs rounded bg-gray-200 px-1 py-0.5 hover:bg-gray-300"
									onclick={cancelTypeEditing}
								>
									Cancel
								</button>
								<button
									class="text-2xs rounded bg-blue-500 px-1 py-0.5 text-white hover:bg-blue-600"
									onclick={saveOutputType}
								>
									Save
								</button>
							</div>
						</div>
					{:else}
						<div
							class="text-2xs group flex items-center justify-between rounded bg-purple-50 px-1 py-0.5"
						>
							<span class="font-mono">{type}</span>
							<div class="flex">
								<button
									class="ml-1 flex h-3 w-3 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity hover:bg-gray-200 hover:text-blue-500 group-hover:opacity-100"
									onclick={() => startEditingOutputType(index)}
									title="Edit type"
								>
									<PencilSimple size={8} weight="bold" />
								</button>
								<button
									class="ml-1 flex h-3 w-3 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
									onclick={() => deleteOutputType(index)}
									title="Remove type"
								>
									<Trash size={8} weight="bold" />
								</button>
							</div>
						</div>
					{/if}
				{/each}
			</div>
		</div>

		<!-- Prompt and System Prompt Sections - Each takes half of remaining space -->
		<div class="flex min-h-0 flex-grow flex-col overflow-hidden">
			<!-- Prompt Section -->
			<div class="mb-2 min-h-0 flex-1">
				<div class="mb-1 flex flex-none items-center">
					<h3 class="text-2xs font-semibold text-gray-600">Prompt</h3>
				</div>
				<div class="h-full">
					<CodeMirror
						value={data.prompt}
						lang={markdown()}
						styles={{
							'&': {
								border: '1px solid #e2e8f0',
								borderRadius: '0.25rem',
								fontSize: '0.7rem',
								height: '100%',
								width: '100%',
								overflow: 'hidden',
								display: 'flex',
								flexDirection: 'column'
							},
							'.cm-content': {
								fontFamily: 'monospace'
							},
							'.cm-scroller': {
								overflow: 'auto'
							},
							'.cm-editor': {
								height: '100%'
							}
						}}
						on:change={handlePromptUpdate}
						basic={true}
					/>
				</div>
			</div>

			<!-- System Prompt Section -->
			<div class="min-h-0 flex-1">
				<div class="mb-1 flex flex-none items-center">
					<h3 class="text-2xs font-semibold text-gray-600">System Prompt</h3>
				</div>
				<div class="h-full">
					<CodeMirror
						value={data.systemPrompt}
						lang={markdown()}
						styles={{
							'&': {
								border: '1px solid #e2e8f0',
								borderRadius: '0.25rem',
								fontSize: '0.7rem',
								height: '100%',
								width: '100%',
								overflow: 'hidden',
								display: 'flex',
								flexDirection: 'column'
							},
							'.cm-content': {
								fontFamily: 'monospace'
							},
							'.cm-scroller': {
								overflow: 'auto'
							},
							'.cm-editor': {
								height: '100%'
							}
						}}
						on:change={handleSystemPromptUpdate}
						basic={true}
					/>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	/* Additional utility class for extra small text */
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
