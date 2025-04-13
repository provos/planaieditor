<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import Trash from 'phosphor-svelte/lib/Trash';

	// Extend the base data interface
	export interface LLMWorkerData extends BaseWorkerData {
		prompt: string;
		systemPrompt: string;
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

	// Ensure all fields are initialized
	if (!data.prompt) {
		data.prompt = '';
	}
	if (!data.systemPrompt) {
		data.systemPrompt = '';
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
</script>

<BaseWorkerNode {id} {data} defaultName="LLMTaskWorker" minHeight={400}>
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
