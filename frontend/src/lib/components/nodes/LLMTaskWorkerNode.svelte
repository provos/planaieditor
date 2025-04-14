<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';
	import { getColorForType } from '$lib/utils/colorUtils';
	import Trash from 'phosphor-svelte/lib/Trash';

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
		isCached?: boolean;
	}

	let { id, data } = $props<{
		id: string;
		data: LLMWorkerData;
	}>();

	// Create local state variables for reactivity
	let availableTaskClasses = $state<string[]>([]);
	let showLLMOutputTypeDropdown = $state(false);
	let currentOutputType = $state(data.llm_output_type || '');
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

	$effect(() => {
		if (currentOutputType && !availableTaskClasses.includes(currentOutputType)) {
			currentOutputType = '';
			data.llm_output_type = '';
		}
	});

	// Sync local state with data object
	$effect(() => {
		currentOutputType = data.llm_output_type || '';
	});

	// Handle code updates
	function handlePromptUpdate(newCode: string) {
		data.prompt = newCode;
	}

	function handleSystemPromptUpdate(newCode: string) {
		data.systemPrompt = newCode;
	}

	// LLM Output Type functions
	function toggleLLMOutputTypeDropdown() {
		showLLMOutputTypeDropdown = !showLLMOutputTypeDropdown;
	}

	function selectLLMOutputType(typeName: string) {
		data.llm_output_type = typeName;
		currentOutputType = typeName;
		showLLMOutputTypeDropdown = false;
	}

	function deleteLLMOutputType() {
		data.llm_output_type = '';
		currentOutputType = '';
	}
</script>

<BaseWorkerNode
	{id}
	{data}
	additionalOutputType={currentOutputType}
	defaultName="LLMTaskWorker"
	minHeight={400}
>
	<!-- LLM Output Type Section -->
	<div class="mb-2 flex-none">
		<h3 class="text-2xs mb-1 font-semibold text-gray-600">LLM Output Type</h3>

		<div class="relative">
			{#if availableTaskClasses.length > 0}
				{#if currentOutputType}
					{@const color = getColorForType(currentOutputType)}
					<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
					<div
						class="text-2xs group flex cursor-pointer items-center justify-between rounded px-1 py-0.5"
						style={`background-color: ${color}20; border-left: 3px solid ${color};`}
						onclick={toggleLLMOutputTypeDropdown}
						role="button"
						tabindex="0"
					>
						<span class="font-mono">{currentOutputType}</span>
						<button
							class="ml-1 flex h-3 w-3 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
							onclick={(e) => {
								e.stopPropagation();
								deleteLLMOutputType();
							}}
							title="Remove type"
						>
							<Trash size={8} weight="bold" />
						</button>
					</div>
				{:else}
					<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
					<div
						class="text-2xs cursor-pointer py-0.5 italic text-gray-400"
						onclick={toggleLLMOutputTypeDropdown}
						role="button"
						tabindex="0"
					>
						Select LLM output type
					</div>
				{/if}
			{:else}
				<div class="text-2xs cursor-pointer py-0.5 italic text-gray-400">
					No output types defined
				</div>
			{/if}

			{#if showLLMOutputTypeDropdown}
				<div class="absolute z-10 mt-1 w-full rounded border border-gray-200 bg-white shadow-md">
					{#each availableTaskClasses as className}
						<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
						<div
							class="text-2xs cursor-pointer p-1 hover:bg-gray-100 {currentOutputType === className
								? 'bg-gray-100'
								: ''}"
							onclick={() => selectLLMOutputType(className)}
							role="button"
							tabindex="0"
						>
							{className}
						</div>
					{/each}
				</div>
			{/if}
		</div>
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
		<!-- Custom method rendering is now handled by BaseWorkerNode -->
	</div>
</BaseWorkerNode>
