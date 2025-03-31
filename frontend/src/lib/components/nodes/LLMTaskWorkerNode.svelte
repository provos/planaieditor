<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { isValidPythonClassName, isValidPythonIdentifier } from '$lib/utils/validation';
	import { allClassNames } from '$lib/stores/classNameStore';
	import Plus from 'phosphor-svelte/lib/Plus';
	import Trash from 'phosphor-svelte/lib/Trash';
	import PencilSimple from 'phosphor-svelte/lib/PencilSimple';
	import Code from 'phosphor-svelte/lib/Code';
	import ChatText from 'phosphor-svelte/lib/ChatText';

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
	let editingPrompt = $state(false);
	let editingSystemPrompt = $state(false);
	let tempWorkerName = $state(data.workerName);
	let tempPrompt = $state(data.prompt);
	let tempSystemPrompt = $state(data.systemPrompt);

	// Type editing states
	let editingInputType = $state<number | null>(null);
	let editingOutputType = $state<number | null>(null);
	let tempType = $state('');
	let typeError = $state('');

	// Track current types for rendering
	let currentInputTypes = $state<string[]>([...data.inputTypes]);
	let currentOutputTypes = $state<string[]>([...data.outputTypes]);

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

	// Input type handling
	function startEditingInputType(index: number = -1) {
		if (index >= 0) {
			tempType = data.inputTypes[index];
		} else {
			tempType = '';
		}
		editingInputType = index;
		typeError = '';
	}

	function saveInputType() {
		if (!validateType(tempType)) return;

		if (editingInputType === -1) {
			// Add new type
			data.inputTypes = [...data.inputTypes, tempType];
		} else {
			// Update existing type
			data.inputTypes = data.inputTypes.map((type: string, i: number) =>
				i === editingInputType ? tempType : type
			);
		}

		currentInputTypes = [...data.inputTypes];
		cancelTypeEditing();
	}

	function deleteInputType(index: number) {
		data.inputTypes = data.inputTypes.filter((_: string, i: number) => i !== index);
		currentInputTypes = [...data.inputTypes];
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
		editingInputType = null;
		editingOutputType = null;
		tempType = '';
		typeError = '';
	}

	// Prompt editing
	function startEditingPrompt() {
		tempPrompt = data.prompt;
		editingPrompt = true;
	}

	function savePrompt() {
		data.prompt = tempPrompt;
		editingPrompt = false;
	}

	function cancelEditingPrompt() {
		tempPrompt = data.prompt;
		editingPrompt = false;
	}

	// System Prompt editing
	function startEditingSystemPrompt() {
		tempSystemPrompt = data.systemPrompt;
		editingSystemPrompt = true;
	}

	function saveSystemPrompt() {
		data.systemPrompt = tempSystemPrompt;
		editingSystemPrompt = false;
	}

	function cancelEditingSystemPrompt() {
		tempSystemPrompt = data.systemPrompt;
		editingSystemPrompt = false;
	}

	// Handle keydown for general editing events
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			cancelTypeEditing();
			cancelEditingPrompt();
			cancelEditingSystemPrompt();
		}
	}

	// Update tracked fields when data changes
	$effect(() => {
		currentInputTypes = [...data.inputTypes];
		currentOutputTypes = [...data.outputTypes];
	});
</script>

<div class="llmtaskworker-node w-64 rounded-md border border-gray-300 bg-white shadow-md">
	<!-- Node handles -->
	<Handle type="target" position={Position.Top} id="input" />
	<Handle type="source" position={Position.Bottom} id="output" />

	<!-- Header with editable worker name -->
	<div class="border-b border-gray-200 bg-gray-50 p-1">
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

	<div class="max-h-64 overflow-y-auto p-1.5">
		<!-- Input Types Section -->
		<div class="mb-2">
			<div class="flex items-center justify-between">
				<h3 class="text-2xs font-semibold text-gray-600">Input Types</h3>
				<button
					class="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-blue-100 text-blue-500 shadow-sm hover:bg-blue-200"
					onclick={() => startEditingInputType(-1)}
					title="Add input type"
				>
					<Plus size={8} weight="bold" />
				</button>
			</div>

			{#if !currentInputTypes.length && editingInputType !== -1}
				<div class="text-2xs py-0.5 italic text-gray-400">No input types</div>
			{/if}

			<div class="mt-1 space-y-1">
				{#each currentInputTypes as type, index}
					{#if editingInputType === index}
						<div class="rounded border border-blue-200 bg-blue-50 p-1">
							<div class="mb-1">
								<input
									type="text"
									bind:value={tempType}
									onkeydown={handleKeydown}
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
									onclick={saveInputType}
								>
									Save
								</button>
							</div>
						</div>
					{:else}
						<div
							class="text-2xs group flex items-center justify-between rounded bg-green-50 px-1 py-0.5"
						>
							<span class="font-mono">{type}</span>
							<div class="flex">
								<button
									class="ml-1 flex h-3 w-3 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity hover:bg-gray-200 hover:text-blue-500 group-hover:opacity-100"
									onclick={() => startEditingInputType(index)}
									title="Edit type"
								>
									<PencilSimple size={8} weight="bold" />
								</button>
								<button
									class="ml-1 flex h-3 w-3 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
									onclick={() => deleteInputType(index)}
									title="Remove type"
								>
									<Trash size={8} weight="bold" />
								</button>
							</div>
						</div>
					{/if}
				{/each}

				{#if editingInputType === -1}
					<div class="rounded border border-blue-200 bg-blue-50 p-1">
						<div class="mb-1">
							<input
								type="text"
								bind:value={tempType}
								onkeydown={handleKeydown}
								placeholder="TaskClassName"
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
								onclick={saveInputType}
							>
								Add
							</button>
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Output Types Section -->
		<div class="mb-2">
			<div class="flex items-center justify-between">
				<h3 class="text-2xs font-semibold text-gray-600">Output Types</h3>
				<button
					class="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-blue-100 text-blue-500 shadow-sm hover:bg-blue-200"
					onclick={() => startEditingOutputType(-1)}
					title="Add output type"
				>
					<Plus size={8} weight="bold" />
				</button>
			</div>

			{#if !currentOutputTypes.length && editingOutputType !== -1}
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
									onkeydown={handleKeydown}
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

				{#if editingOutputType === -1}
					<div class="rounded border border-blue-200 bg-blue-50 p-1">
						<div class="mb-1">
							<input
								type="text"
								bind:value={tempType}
								onkeydown={handleKeydown}
								placeholder="TaskClassName"
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
								Add
							</button>
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Prompt Section -->
		<div class="mt-3">
			<div class="flex items-center justify-between">
				<h3 class="text-2xs font-semibold text-gray-600">Prompt</h3>
				<button
					class="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-blue-100 text-blue-500 shadow-sm hover:bg-blue-200"
					onclick={startEditingPrompt}
					title="Edit prompt"
				>
					<ChatText size={8} weight="bold" />
				</button>
			</div>

			{#if editingPrompt}
				<div class="mt-1 rounded border border-blue-200 bg-blue-50 p-1">
					<div class="mb-1">
						<textarea
							bind:value={tempPrompt}
							class="text-2xs h-24 w-full rounded border border-gray-200 bg-gray-50 px-1.5 py-1 font-mono"
							style="resize: vertical;"
							placeholder="Enter prompt text here..."
						></textarea>
					</div>
					<div class="flex justify-end space-x-1">
						<button
							class="text-2xs rounded bg-gray-200 px-1 py-0.5 hover:bg-gray-300"
							onclick={cancelEditingPrompt}
						>
							Cancel
						</button>
						<button
							class="text-2xs rounded bg-blue-500 px-1 py-0.5 text-white hover:bg-blue-600"
							onclick={savePrompt}
						>
							Save
						</button>
					</div>
				</div>
			{:else}
				<div class="mt-1 max-h-16 overflow-auto rounded border border-gray-200 bg-gray-50 p-1">
					{#if data.prompt}
						<pre class="text-2xs whitespace-pre-wrap font-mono">{data.prompt}</pre>
					{:else}
						<div class="text-2xs py-0.5 italic text-gray-400">No prompt defined</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- System Prompt Section -->
		<div class="mt-3">
			<div class="flex items-center justify-between">
				<h3 class="text-2xs font-semibold text-gray-600">System Prompt</h3>
				<button
					class="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-blue-100 text-blue-500 shadow-sm hover:bg-blue-200"
					onclick={startEditingSystemPrompt}
					title="Edit system prompt"
				>
					<ChatText size={8} weight="bold" />
				</button>
			</div>

			{#if editingSystemPrompt}
				<div class="mt-1 rounded border border-blue-200 bg-blue-50 p-1">
					<div class="mb-1">
						<textarea
							bind:value={tempSystemPrompt}
							class="text-2xs h-24 w-full rounded border border-gray-200 bg-gray-50 px-1.5 py-1 font-mono"
							style="resize: vertical;"
							placeholder="Enter system prompt text here..."
						></textarea>
					</div>
					<div class="flex justify-end space-x-1">
						<button
							class="text-2xs rounded bg-gray-200 px-1 py-0.5 hover:bg-gray-300"
							onclick={cancelEditingSystemPrompt}
						>
							Cancel
						</button>
						<button
							class="text-2xs rounded bg-blue-500 px-1 py-0.5 text-white hover:bg-blue-600"
							onclick={saveSystemPrompt}
						>
							Save
						</button>
					</div>
				</div>
			{:else}
				<div class="mt-1 max-h-16 overflow-auto rounded border border-gray-200 bg-gray-50 p-1">
					{#if data.systemPrompt}
						<pre class="text-2xs whitespace-pre-wrap font-mono">{data.systemPrompt}</pre>
					{:else}
						<div class="text-2xs py-0.5 italic text-gray-400">No system prompt defined</div>
					{/if}
				</div>
			{/if}
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
