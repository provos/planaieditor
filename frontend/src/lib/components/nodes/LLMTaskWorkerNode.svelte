<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';
	import { getColorForType } from '$lib/utils/colorUtils';
	import Trash from 'phosphor-svelte/lib/Trash';
	import { useUpdateNodeInternals } from '@xyflow/svelte';
	import { tick } from 'svelte';
	import type { Action } from 'svelte/action';
	import { llmConfigs } from '$lib/stores/llmConfigsStore';
	import { getProviderVisuals } from '$lib/utils/providerVisuals';
	import { getLLMConfigByName } from '$lib/stores/llmConfigsStore';

	// Extend the base data interface
	export interface LLMWorkerData extends BaseWorkerData {
		prompt: string;
		system_prompt: string;
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
		// Add simple boolean flags
		use_xml: boolean;
		debug_mode: boolean;
		llmConfigName?: string;
	}

	let { id, data } = $props<{
		id: string;
		data: LLMWorkerData;
	}>();

	const updateNodeInternals = useUpdateNodeInternals();

	// Create local state variables for reactivity
	let availableTaskClasses = $state<string[]>([]);
	let showLLMOutputTypeDropdown = $state(false);
	let currentOutputType = $state(data.llm_output_type || '');
	// Ensure all fields are initialized
	if (!data.prompt) {
		data.prompt = '';
	}
	if (!data.system_prompt) {
		data.system_prompt = '';
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

	// Initialize boolean flags if not present
	if (data.use_xml === undefined) {
		data.use_xml = false;
	}
	if (data.debug_mode === undefined) {
		data.debug_mode = false;
	}

	// Local state for boolean flags
	let useXml = $state(data.use_xml);
	let debugMode = $state(data.debug_mode);

	// Local reactive state for the LLM config name selection
	let selectedLLMConfigName = $state(data.llmConfigName);

	// Derived state for selected config visuals
	let selectedConfigVisuals = $derived.by(() => {
		if (selectedLLMConfigName) {
			// Depend on the local reactive state
			const config = getLLMConfigByName(selectedLLMConfigName);
			if (config) {
				return getProviderVisuals(config.provider);
			}
		}
		return null;
	});

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

	// Sync local checkbox state back to data prop
	$effect(() => {
		data.use_xml = useXml;
	});

	$effect(() => {
		data.debug_mode = debugMode;
	});

	// Sync local state back to the data prop when the user changes the selection
	$effect(() => {
		data.llmConfigName = selectedLLMConfigName;
	});

	// Handle code updates
	function handlePromptUpdate(newCode: string) {
		data.prompt = newCode;
	}

	function handleSystemPromptUpdate(newCode: string) {
		data.system_prompt = newCode;
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

	async function handleCollapse() {
		await tick();
		updateNodeInternals(id);
	}

	// Action to detect clicks outside an element
	const clickOutside: Action<HTMLElement, () => void> = (node, callback) => {
		const handleClick = (event: MouseEvent) => {
			if (
				node &&
				!node.contains(event.target as Node) &&
				!event.defaultPrevented &&
				callback // Ensure callback exists
			) {
				// Call the callback directly
				callback();
			}
		};

		// Use capture phase to catch clicks even if event propagation is stopped
		document.addEventListener('click', handleClick, true);

		return {
			destroy() {
				document.removeEventListener('click', handleClick, true);
			}
		};
	};

	// Close dropdown on Escape key press when trigger has focus
	function handleTriggerKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && showLLMOutputTypeDropdown) {
			showLLMOutputTypeDropdown = false;
			event.stopPropagation();
		}
	}
</script>

<BaseWorkerNode
	{id}
	{data}
	additionalOutputType={currentOutputType}
	defaultName="LLMTaskWorker"
	minHeight={400}
	isCached={data.isCached}
>
	<!-- LLM Configuration Selector -->
	<div class="mb-2 flex-none">
		<label for="llm-config-{id}" class="label flex-none">LLM Config</label>
		<div class="mt-1 flex items-center gap-2">
			{#if selectedConfigVisuals}
				<div class="flex-none" title={data.llmConfigName}>
					<selectedConfigVisuals.icon size={12} class={selectedConfigVisuals.colorClass} />
				</div>
			{/if}
			<select
				id="llm-config-{id}"
				class="text-2xs nodrag select select-bordered select-sm w-full flex-grow"
				bind:value={selectedLLMConfigName}
			>
				<option value={undefined}>-- Select --</option>
				{#if $llmConfigs.length === 0}
					<option disabled>No configs defined</option>
				{/if}
				{#each $llmConfigs as config (config.id)}
					<option value={config.name}>{config.name}</option>
				{/each}
			</select>
		</div>
	</div>

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
						onkeydown={handleTriggerKeydown}
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
						onkeydown={handleTriggerKeydown}
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
				<div
					class="absolute z-10 mt-1 w-full rounded border border-gray-200 bg-white shadow-md"
					use:clickOutside={() => (showLLMOutputTypeDropdown = false)}
				>
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

	<!-- New Settings Section -->
	<div class="mb-2 flex-none border-t border-gray-200 pt-2">
		<h3 class="text-2xs mb-1 font-semibold text-gray-600">Settings</h3>
		<div class="flex items-center space-x-4">
			<label class="text-2xs flex items-center">
				<input type="checkbox" class="mr-1 h-2.5 w-2.5" bind:checked={useXml} />
				Use XML Output
			</label>
			<label class="text-2xs flex items-center">
				<input type="checkbox" class="mr-1 h-2.5 w-2.5" bind:checked={debugMode} />
				Debug Mode
			</label>
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
			onCollapseToggle={handleCollapse}
		/>
		<EditableCodeSection
			title="System Prompt"
			code={data.system_prompt}
			language="markdown"
			onUpdate={handleSystemPromptUpdate}
			onCollapseToggle={handleCollapse}
		/>

		<!-- Customizable functions -->
		<!-- Custom method rendering is now handled by BaseWorkerNode -->
	</div>
</BaseWorkerNode>

<style>
	@reference "tailwindcss";

	.text-2xs {
		font-size: 0.65rem; /* 10.4px */
		line-height: 1rem; /* 16px */
	}

	.label {
		/* @apply text-2xs font-semibold text-gray-600; */
		font-size: 0.65rem; /* Apply text-2xs size directly */
		line-height: 1rem; /* Apply text-2xs line-height directly */
		font-weight: 600; /* Corresponds to font-semibold */
		color: rgb(75 85 99); /* Corresponds to text-gray-600 */
	}
</style>
