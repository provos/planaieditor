<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';
	import { getColorForType } from '$lib/utils/colorUtils';

	// Extend the base data interface
	export interface LLMWorkerData extends BaseWorkerData {
		prompt: string;
		systemPrompt: string;
		llm_output_type?: string;
		extraValidation: string;
		formatPrompt: string;
		preProcess: string;
		postProcess: string;
		editingFunction?: string | null;
		// Track which functions are enabled
		enabledFunctions: {
			extraValidation: boolean;
			formatPrompt: boolean;
			preProcess: boolean;
			postProcess: boolean;
		};
	}

	let { id, data } = $props<{
		id: string;
		data: LLMWorkerData;
	}>();

	// Create local state variables for reactivity
	let enabledExtraValidation = $state(false);
	let enabledFormatPrompt = $state(false);
	let enabledPreProcess = $state(false);
	let enabledPostProcess = $state(false);
	let availableTaskClasses = $state<string[]>([]);
	let editingLLMOutputType = $state(false);
	let tempLLMOutputType = $state('');

	// Ensure all fields are initialized
	if (!data.prompt) {
		data.prompt = '';
	}
	if (!data.systemPrompt) {
		data.systemPrompt = '';
	}
	if (!data.llm_output_type) {
		data.llm_output_type = '';
	}

	// Initialize default function code
	const defaultExtraValidation = `return None`;
	const defaultFormatPrompt = `return self.prompt`;
	const defaultPreProcess = `return task`;
	const defaultPostProcess = `return super().post_process(response, input_task)`;

	// Initialize function code
	if (!data.extraValidation) {
		data.extraValidation = defaultExtraValidation;
	}
	if (!data.formatPrompt) {
		data.formatPrompt = defaultFormatPrompt;
	}
	if (!data.preProcess) {
		data.preProcess = defaultPreProcess;
	}
	if (!data.postProcess) {
		data.postProcess = defaultPostProcess;
	}

	// Initialize enabled functions
	if (!data.enabledFunctions) {
		data.enabledFunctions = {
			extraValidation: false,
			formatPrompt: false,
			preProcess: false,
			postProcess: false
		};
	}

	// Subscribe to the taskClassNamesStore for output type selection
	$effect(() => {
		const unsubClassNames = taskClassNamesStore.subscribe((taskClasses) => {
			availableTaskClasses = Array.from(taskClasses);
		});

		return unsubClassNames;
	});

	// Sync local state with data object
	$effect(() => {
		enabledExtraValidation = data.enabledFunctions.extraValidation;
		enabledFormatPrompt = data.enabledFunctions.formatPrompt;
		enabledPreProcess = data.enabledFunctions.preProcess;
		enabledPostProcess = data.enabledFunctions.postProcess;
	});

	// Sync data object with local state
	$effect(() => {
		data.enabledFunctions = {
			extraValidation: enabledExtraValidation,
			formatPrompt: enabledFormatPrompt,
			preProcess: enabledPreProcess,
			postProcess: enabledPostProcess
		};
	});

	// Handle code updates
	function handlePromptUpdate(newCode: string) {
		data.prompt = newCode;
	}

	function handleSystemPromptUpdate(newCode: string) {
		data.systemPrompt = newCode;
	}

	function handleExtraValidationUpdate(newCode: string) {
		data.extraValidation = newCode;
	}

	function handleFormatPromptUpdate(newCode: string) {
		data.formatPrompt = newCode;
	}

	function handlePreProcessUpdate(newCode: string) {
		data.preProcess = newCode;
	}

	function handlePostProcessUpdate(newCode: string) {
		data.postProcess = newCode;
	}

	// When a function is chosen from the context menu, enable it
	$effect(() => {
		if (data.editingFunction) {
			switch (data.editingFunction) {
				case 'extraValidation':
					enabledExtraValidation = true;
					break;
				case 'formatPrompt':
					enabledFormatPrompt = true;
					break;
				case 'preProcess':
					enabledPreProcess = true;
					break;
				case 'postProcess':
					enabledPostProcess = true;
					break;
			}
			data.editingFunction = null; // Clear it after enabling
		}
	});

	// Reset function to default implementation
	function resetFunction(functionName: string) {
		// Update local state
		switch (functionName) {
			case 'extraValidation':
				enabledExtraValidation = false;
				data.extraValidation = defaultExtraValidation;
				break;
			case 'formatPrompt':
				enabledFormatPrompt = false;
				data.formatPrompt = defaultFormatPrompt;
				break;
			case 'preProcess':
				enabledPreProcess = false;
				data.preProcess = defaultPreProcess;
				break;
			case 'postProcess':
				enabledPostProcess = false;
				data.postProcess = defaultPostProcess;
				break;
		}
	}

	// LLM Output Type functions
	function startEditingLLMOutputType() {
		tempLLMOutputType = data.llm_output_type || '';
		editingLLMOutputType = true;
	}

	function updateLLMOutputType() {
		data.llm_output_type = tempLLMOutputType;
		editingLLMOutputType = false;
	}

	function cancelEditingLLMOutputType() {
		tempLLMOutputType = data.llm_output_type || '';
		editingLLMOutputType = false;
	}

	function handleLLMTypeKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') updateLLMOutputType();
		else if (event.key === 'Escape') cancelEditingLLMOutputType();
	}

	function setLLMOutputTypeFromSelect(event: Event) {
		const select = event.target as HTMLSelectElement;
		if (select && select.value) {
			data.llm_output_type = select.value;
			select.value = ''; // Reset select
		}
	}
</script>

<BaseWorkerNode {id} {data} defaultName="LLMTaskWorker" minHeight={400}>
	<!-- LLM Output Type Section -->
	<div class="mb-2 flex-none">
		<h3 class="text-2xs mb-1 font-semibold text-gray-600">LLM Output Type</h3>
		<div class="mb-1">
			<select
				class="text-2xs w-full rounded border border-gray-200 px-1 py-0.5"
				onchange={setLLMOutputTypeFromSelect}
			>
				<option value="">Select LLM output type...</option>
				{#each availableTaskClasses as className}
					<option value={className} selected={data.llm_output_type === className}
						>{className}</option
					>
				{/each}
			</select>
		</div>

		{#if data.llm_output_type}
			{@const color = getColorForType(data.llm_output_type)}
			{#if editingLLMOutputType}
				<!-- LLM Output Type Edit Form -->
				<div class="rounded border border-blue-200 bg-blue-50 p-1">
					<div class="mb-1">
						<input
							type="text"
							bind:value={tempLLMOutputType}
							onkeydown={handleLLMTypeKeydown}
							class="text-2xs w-full rounded border border-gray-200 px-1 py-0.5"
							autofocus
						/>
					</div>
					<div class="flex justify-end space-x-1">
						<button
							class="text-2xs rounded bg-gray-200 px-1 py-0.5 hover:bg-gray-300"
							onclick={cancelEditingLLMOutputType}>Cancel</button
						>
						<button
							class="text-2xs rounded bg-blue-500 px-1 py-0.5 text-white hover:bg-blue-600"
							onclick={updateLLMOutputType}>Save</button
						>
					</div>
				</div>
			{:else}
				<!-- LLM Output Type Display -->
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<div
					class="text-2xs flex items-center justify-between rounded px-1 py-0.5"
					style={`background-color: ${color}20; border-left: 3px solid ${color};`}
					onclick={startEditingLLMOutputType}
					role="button"
					tabindex="0"
				>
					<span class="font-mono">{data.llm_output_type}</span>
				</div>
			{/if}
		{:else}
			<div class="text-2xs py-0.5 italic text-gray-400">No LLM output type defined</div>
		{/if}
	</div>

	<!-- Prompt and System Prompt Sections using new component -->
	<div class="flex min-h-0 flex-grow flex-col space-y-3 overflow-auto p-1">
		<!-- Main prompt sections always shown -->
		<EditableCodeSection
			title="Prompt"
			code={data.prompt}
			language="markdown"
			onUpdate={handlePromptUpdate}
		/>
		<EditableCodeSection
			title="System Prompt"
			code={data.systemPrompt}
			language="markdown"
			onUpdate={handleSystemPromptUpdate}
		/>

		<!-- Customizable functions -->
		<div class="mt-3 space-y-3">
			<!-- Extra Validation Function -->
			{#if enabledExtraValidation}
				<EditableCodeSection
					title="def extra_validation(self, response: Task, input_task: Task) -> Optional[str]:"
					code={data.extraValidation}
					language="python"
					onUpdate={handleExtraValidationUpdate}
					showReset={true}
					onReset={() => resetFunction('extraValidation')}
				/>
			{/if}

			<!-- Format Prompt Function -->
			{#if enabledFormatPrompt}
				<EditableCodeSection
					title="def format_prompt(self, task: Task) -> str:"
					code={data.formatPrompt}
					language="python"
					onUpdate={handleFormatPromptUpdate}
					showReset={true}
					onReset={() => resetFunction('formatPrompt')}
				/>
			{/if}

			<!-- Pre Process Function -->
			{#if enabledPreProcess}
				<EditableCodeSection
					title="def pre_process(self, task: Task) -> Optional[Task]:"
					code={data.preProcess}
					language="python"
					onUpdate={handlePreProcessUpdate}
					showReset={true}
					onReset={() => resetFunction('preProcess')}
				/>
			{/if}

			<!-- Post Process Function -->
			{#if enabledPostProcess}
				<EditableCodeSection
					title="def post_process(self, response: Optional[Task], input_task: Task):"
					code={data.postProcess}
					language="python"
					onUpdate={handlePostProcessUpdate}
					showReset={true}
					onReset={() => resetFunction('postProcess')}
				/>
			{/if}
		</div>
	</div>
</BaseWorkerNode>
