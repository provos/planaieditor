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
	const defaultExtraValidation = `def extra_validation(self, response: Task, input_task: Task) -> Optional[str]:
    """
    Validates the response from the LLM.
    Override this method to do additional validation.

    Returns:
        Optional[str]: An error message if invalid, None otherwise.
    """
    return None`;

	const defaultFormatPrompt = `def format_prompt(self, task: Task) -> str:
    """
    Formats the prompt for the LLM based on the input task.

    Returns:
        str: The formatted prompt.
    """
    return self.prompt`;

	const defaultPreProcess = `def pre_process(self, task: Task) -> Optional[Task]:
    """
    Pre-processes the input task before sending to the LLM.

    Returns:
        Task: The pre-processed task or None.
    """
    return task`;

	const defaultPostProcess = `def post_process(self, response: Optional[Task], input_task: Task):
    """
    Post-processes the response and publishes the work.

    Args:
        response (Optional[Task]): The response from LLM.
        input_task (Task): The input task.
    """
    if response is not None:
        self.publish_work(task=response, input_task=input_task)
    else:
        logging.error(
            "LLM did not return a valid response for task %s with provenance %s",
            input_task.name,
            input_task._provenance,
        )`;

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
				<div class="rounded-md border border-gray-200 p-2">
					<EditableCodeSection
						title="def extra_validation(self, response: Task, input_task: Task) -> Optional[str]:"
						code={data.extraValidation}
						language="python"
						onUpdate={handleExtraValidationUpdate}
						showReset={true}
						onReset={() => resetFunction('extraValidation')}
					/>
				</div>
			{/if}

			<!-- Format Prompt Function -->
			{#if enabledFormatPrompt}
				<div class="rounded-md border border-gray-200 p-2">
					<EditableCodeSection
						title="def format_prompt(self, task: Task) -> str:"
						code={data.formatPrompt}
						language="python"
						onUpdate={handleFormatPromptUpdate}
						showReset={true}
						onReset={() => resetFunction('formatPrompt')}
					/>
				</div>
			{/if}

			<!-- Pre Process Function -->
			{#if enabledPreProcess}
				<div class="rounded-md border border-gray-200 p-2">
					<EditableCodeSection
						title="def pre_process(self, task: Task) -> Optional[Task]:"
						code={data.preProcess}
						language="python"
						onUpdate={handlePreProcessUpdate}
						showReset={true}
						onReset={() => resetFunction('preProcess')}
					/>
				</div>
			{/if}

			<!-- Post Process Function -->
			{#if enabledPostProcess}
				<div class="rounded-md border border-gray-200 p-2">
					<EditableCodeSection
						title="def post_process(self, response: Optional[Task], input_task: Task):"
						code={data.postProcess}
						language="python"
						onUpdate={handlePostProcessUpdate}
						showReset={true}
						onReset={() => resetFunction('postProcess')}
					/>
				</div>
			{/if}
		</div>
	</div>
</BaseWorkerNode>

<style>
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
