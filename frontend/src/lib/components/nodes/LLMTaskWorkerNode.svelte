<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import LLMConfigSelector from '$lib/components/LLMConfigSelector.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';
	import { getColorForType } from '$lib/utils/colorUtils';
	import Trash from 'phosphor-svelte/lib/Trash';
	import { useUpdateNodeInternals, useStore } from '@xyflow/svelte';
	import { tick } from 'svelte';
	import type { Action } from 'svelte/action';
	import { addAvailableMethod } from '$lib/utils/nodeUtils';
	import type { Unsubscriber } from 'svelte/store';
	import { persistNodeDataDebounced } from '$lib/utils/nodeUtils';

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
		use_xml: boolean;
		debug_mode: boolean;
		llmConfigName?: string;
		llmConfigFromCode?: Record<string, any>;
		llmConfigVar?: string;
	}

	let { id, data } = $props<{
		id: string;
		data: LLMWorkerData;
	}>();

	const updateNodeInternals = useUpdateNodeInternals();
	const { nodes } = useStore();

	// Create local state variables for reactivity
	let availableTaskClasses = $state<string[]>([]);
	let showLLMOutputTypeDropdown = $state(false);
	let currentLLMOutputType = $state(data.llm_output_type || '');
	let nodeOutputTypes = $state<string[]>([]);
	let nodeUnsubscribe: Unsubscriber | null = null;

	// Ensures that we create a post_process if the llm output type does not match the node output types
	$effect(() => {
		if (!currentLLMOutputType) {
			if (nodeUnsubscribe !== null) {
				nodeUnsubscribe();
				nodeUnsubscribe = null;
			}
			return;
		}

		if (nodeUnsubscribe !== null) {
			return;
		}

		nodeUnsubscribe = nodes.subscribe((values) => {
			// find the node with the same id as the current node
			const node = values.find((node) => node.id === id);
			if (node && (node.data as LLMWorkerData).output_types !== $state.snapshot(nodeOutputTypes)) {
				nodeOutputTypes = (node.data as LLMWorkerData).output_types;
				if ((node.data as LLMWorkerData).methods?.post_process) {
					// we already have a post_process method and don't need to add it
					return;
				}

				let needExtraMethod = false;
				if (nodeOutputTypes.length > 1) {
					needExtraMethod = true;
				} else if (
					nodeOutputTypes.length == 1 &&
					nodeOutputTypes[0] != $state.snapshot(currentLLMOutputType)
				) {
					needExtraMethod = true;
				}
				if (needExtraMethod) {
					addAvailableMethod(nodes, id, 'post_process');
				}
			}
		});
	});

	// Local state for boolean flags
	let useXml = $state(data.use_xml);
	let debugMode = $state(data.debug_mode);

	// Ensure all fields are initialized
	if (!data.prompt) {
		data.prompt = '';
		persistNodeDataDebounced(id, nodes, data);
	}
	if (!data.system_prompt) {
		data.system_prompt = '';
		persistNodeDataDebounced(id, nodes, data);
	}
	if (!data.llm_output_type) {
		data.llm_output_type = '';
		persistNodeDataDebounced(id, nodes, data);
	}

	// Initialize default function code
	const defaultExtraValidation = `return None`;
	const defaultFormatPrompt = `return self.prompt`;
	const defaultPreProcess = `return task`;
	const defaultPostProcess = `return super().post_process(response, input_task)`;

	// Initialize function code
	if (!data.extraValidation) {
		data.extraValidation = defaultExtraValidation;
		persistNodeDataDebounced(id, nodes, data);
	}
	if (!data.formatPrompt) {
		data.formatPrompt = defaultFormatPrompt;
		persistNodeDataDebounced(id, nodes, data);
	}
	if (!data.preProcess) {
		data.preProcess = defaultPreProcess;
		persistNodeDataDebounced(id, nodes, data);
	}
	if (!data.postProcess) {
		data.postProcess = defaultPostProcess;
		persistNodeDataDebounced(id, nodes, data);
	}

	// Initialize enabled functions
	if (!data.enabledFunctions) {
		data.enabledFunctions = {
			extraValidation: false,
			formatPrompt: false,
			preProcess: false,
			postProcess: false
		};
		persistNodeDataDebounced(id, nodes, data);
	}

	// Initialize boolean flags if not present
	if (data.use_xml === undefined) {
		data.use_xml = false;
		persistNodeDataDebounced(id, nodes, data);
	}
	if (data.debug_mode === undefined) {
		data.debug_mode = false;
		persistNodeDataDebounced(id, nodes, data);
	}

	// Subscribe to the taskClassNamesStore for output type selection
	$effect(() => {
		const unsubClassNames = taskClassNamesStore.subscribe((taskClasses) => {
			availableTaskClasses = Array.from(taskClasses);
		});

		return unsubClassNames;
	});

	$effect(() => {
		if (currentLLMOutputType && !availableTaskClasses.includes(currentLLMOutputType)) {
			currentLLMOutputType = '';
			data.llm_output_type = '';
			persistNodeDataDebounced(id, nodes, data);
		}
	});

	// Sync local state with data object
	$effect(() => {
		if (data.use_xml !== useXml) {
			data.use_xml = useXml;
			persistNodeDataDebounced(id, nodes, data);
		}
	});

	$effect(() => {
		if (data.debug_mode !== debugMode) {
			data.debug_mode = debugMode;
			persistNodeDataDebounced(id, nodes, data);
		}
	});

	// Handle LLM config changes
	function handleLLMConfigChange(changes: {
		configName?: string;
		configFromCode?: Record<string, any>;
		configVar?: string;
	}) {
		data.llmConfigName = changes.configName;
		data.llmConfigFromCode = changes.configFromCode;
		data.llmConfigVar = changes.configVar;
		persistNodeDataDebounced(id, nodes, data);
	}

	// Handle code updates
	function handlePromptUpdate(newCode: string) {
		data.prompt = newCode;
		persistNodeDataDebounced(id, nodes, data);
	}

	function handleSystemPromptUpdate(newCode: string) {
		data.system_prompt = newCode;
		persistNodeDataDebounced(id, nodes, data);
	}

	// LLM Output Type functions
	function toggleLLMOutputTypeDropdown() {
		showLLMOutputTypeDropdown = !showLLMOutputTypeDropdown;
	}

	function selectLLMOutputType(typeName: string) {
		data.llm_output_type = typeName;
		currentLLMOutputType = typeName;
		showLLMOutputTypeDropdown = false;
		persistNodeDataDebounced(id, nodes, data);
	}

	function deleteLLMOutputType() {
		data.llm_output_type = '';
		currentLLMOutputType = '';
		persistNodeDataDebounced(id, nodes, data);
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
	additionalOutputType={currentLLMOutputType}
	defaultName="LLMTaskWorker"
	minHeight={400}
>
	<!-- LLM Configuration Selector -->
	<LLMConfigSelector
		{id}
		initialConfigName={data.llmConfigName}
		initialConfigFromCode={data.llmConfigFromCode}
		initialConfigVar={data.llmConfigVar}
		onChange={handleLLMConfigChange}
	/>

	<!-- LLM Output Type Section -->
	<div class="mb-2 flex-none">
		<h3 class="text-2xs mb-1 font-semibold text-gray-600">LLM Output Type</h3>

		<div class="relative">
			{#if availableTaskClasses.length > 0}
				{#if currentLLMOutputType}
					{@const color = getColorForType(currentLLMOutputType)}
					<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
					<div
						class="text-2xs group flex cursor-pointer items-center justify-between rounded px-1 py-0.5"
						style={`background-color: ${color}20; border-left: 3px solid ${color};`}
						onclick={toggleLLMOutputTypeDropdown}
						role="button"
						tabindex="0"
						onkeydown={handleTriggerKeydown}
					>
						<span class="font-mono">{currentLLMOutputType}</span>
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
							class="text-2xs cursor-pointer p-1 hover:bg-gray-100 {currentLLMOutputType ===
							className
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
			onUpdateSize={handleCollapse}
		/>
		<EditableCodeSection
			title="System Prompt"
			code={data.system_prompt}
			language="markdown"
			onUpdate={handleSystemPromptUpdate}
			onUpdateSize={handleCollapse}
		/>

		<!-- Customizable functions -->
		<!-- Custom method rendering is now handled by BaseWorkerNode -->
	</div>
</BaseWorkerNode>

<style lang="postcss">
	@reference "tailwindcss";

	.text-2xs {
		font-size: 0.65rem; /* 10.4px */
		line-height: 1rem; /* 16px */
	}
</style>
