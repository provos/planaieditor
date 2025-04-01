<script lang="ts">
	import { Handle, Position, NodeResizer } from '@xyflow/svelte';
	import { isValidPythonClassName, isValidPythonIdentifier } from '$lib/utils/validation';
	import { allClassNames } from '$lib/stores/classNameStore';
	import Plus from 'phosphor-svelte/lib/Plus';
	import Trash from 'phosphor-svelte/lib/Trash';
	import PencilSimple from 'phosphor-svelte/lib/PencilSimple';
	import Code from 'phosphor-svelte/lib/Code';
	import ArrowsIn from 'phosphor-svelte/lib/ArrowsIn';

	interface JoinedWorkerData {
		workerName: string;
		nodeId: string;
		inputTypes: string[];
		outputTypes: string[];
		consumeWork: string;
		joinMethod: 'merge' | 'zip' | 'custom';
	}

	let { id, data } = $props<{
		id: string;
		data: JoinedWorkerData;
	}>();

	// Ensure data fields are initialized
	if (!data.inputTypes) {
		data.inputTypes = [];
	}
	if (!data.outputTypes) {
		data.outputTypes = [];
	}
	if (!data.consumeWork) {
		data.consumeWork = `def consume_work(self, task):
    # Process the input task
    # self.publish_work(output_task, input_task=task)
    pass`;
	}
	if (!data.joinMethod) {
		data.joinMethod = 'merge';
	}

	// State variables
	let editingWorkerName = $state(false);
	let nameError = $state('');
	let editingCode = $state(false);
	let tempWorkerName = $state(data.workerName);
	let tempCode = $state(data.consumeWork);

	// Type editing states
	let editingInputType = $state<number | null>(null);
	let editingOutputType = $state<number | null>(null);
	let tempType = $state('');
	let typeError = $state('');

	// Track current types for rendering
	let currentInputTypes = $state<string[]>([...data.inputTypes]);
	let currentOutputTypes = $state<string[]>([...data.outputTypes]);

	// Join method state
	let joinMethod = $state(data.joinMethod);

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

	// Code editing
	function startEditingCode() {
		tempCode = data.consumeWork;
		editingCode = true;
	}

	function saveCode() {
		data.consumeWork = tempCode;
		editingCode = false;
	}

	function cancelEditingCode() {
		tempCode = data.consumeWork;
		editingCode = false;
	}

	// Join method handling
	function updateJoinMethod(method: 'merge' | 'zip' | 'custom') {
		data.joinMethod = method;
		joinMethod = method;
	}

	// Handle keydown for general editing events
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			cancelTypeEditing();
			cancelEditingCode();
		}
	}

	// Update tracked fields when data changes
	$effect(() => {
		currentInputTypes = [...data.inputTypes];
		currentOutputTypes = [...data.outputTypes];
		joinMethod = data.joinMethod;
	});
</script>

<div
	class="joinedtaskworker-node flex h-full flex-col rounded-md border border-gray-300 bg-white shadow-md"
>
	<!-- Node Resizer -->
	<NodeResizer minWidth={250} minHeight={200} />

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
				{data.workerName || 'JoinedTaskWorker'}
			</div>
		{/if}
	</div>

	<div class="flex h-full min-h-0 flex-col overflow-hidden p-1.5">
		<!-- Input Types Section -->
		<div class="mb-2 flex-none">
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
		<div class="mb-2 flex-none">
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

		<!-- Join Method Section -->
		<div class="mb-2 flex-none">
			<div class="flex items-center justify-between">
				<h3 class="text-2xs font-semibold text-gray-600">Join Method</h3>
				<div
					class="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-blue-100 text-blue-500 shadow-sm"
				>
					<ArrowsIn size={8} weight="bold" />
				</div>
			</div>

			<div class="mt-1 grid grid-cols-3 gap-1">
				<button
					class="text-2xs rounded border px-2 py-0.5 {joinMethod === 'merge'
						? 'border-blue-500 bg-blue-50 text-blue-700'
						: 'border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100'}"
					onclick={() => updateJoinMethod('merge')}
				>
					Merge
				</button>
				<button
					class="text-2xs rounded border px-2 py-0.5 {joinMethod === 'zip'
						? 'border-blue-500 bg-blue-50 text-blue-700'
						: 'border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100'}"
					onclick={() => updateJoinMethod('zip')}
				>
					Zip
				</button>
				<button
					class="text-2xs rounded border px-2 py-0.5 {joinMethod === 'custom'
						? 'border-blue-500 bg-blue-50 text-blue-700'
						: 'border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100'}"
					onclick={() => updateJoinMethod('custom')}
				>
					Custom
				</button>
			</div>
		</div>

		<!-- Code Section (only shown when join method is 'custom') -->
		{#if joinMethod === 'custom'}
			<div class="flex min-h-0 flex-grow flex-col overflow-hidden">
				<div class="mb-1 flex flex-none items-center justify-between">
					<h3 class="text-2xs font-semibold text-gray-600">consume_work()</h3>
					<button
						class="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-blue-100 text-blue-500 shadow-sm hover:bg-blue-200"
						onclick={startEditingCode}
						title="Edit code"
					>
						<Code size={8} weight="bold" />
					</button>
				</div>

				{#if editingCode}
					<div
						class="flex min-h-0 flex-grow flex-col rounded border border-blue-200 bg-blue-50 p-1"
					>
						<div class="min-h-0 flex-grow">
							<textarea
								bind:value={tempCode}
								class="text-2xs h-full w-full rounded border border-gray-200 bg-gray-50 px-1.5 py-1 font-mono"
								style="resize: none;"
							></textarea>
						</div>
						<div class="mt-1 flex flex-none justify-end space-x-1">
							<button
								class="text-2xs rounded bg-gray-200 px-1 py-0.5 hover:bg-gray-300"
								onclick={cancelEditingCode}
							>
								Cancel
							</button>
							<button
								class="text-2xs rounded bg-blue-500 px-1 py-0.5 text-white hover:bg-blue-600"
								onclick={saveCode}
							>
								Save
							</button>
						</div>
					</div>
				{:else}
					<div class="flex-grow overflow-auto rounded border border-gray-200 bg-gray-50 p-1">
						<pre class="text-2xs whitespace-pre-wrap font-mono">{data.consumeWork}</pre>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	/* Additional utility class for extra small text */
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
