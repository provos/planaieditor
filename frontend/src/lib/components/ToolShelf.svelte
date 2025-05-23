<script lang="ts">
	import Eraser from 'phosphor-svelte/lib/Eraser';
	import UploadSimple from 'phosphor-svelte/lib/UploadSimple';
	import PythonInterpreterSelector from '$lib/components/PythonInterpreterSelector.svelte';
	import Export from 'phosphor-svelte/lib/Export';
	import Play from 'phosphor-svelte/lib/Play';
	import Gear from 'phosphor-svelte/lib/Gear';
	import FloppyDisk from 'phosphor-svelte/lib/FloppyDisk';
	import FolderOpen from 'phosphor-svelte/lib/FolderOpen';
	import Robot from 'phosphor-svelte/lib/Robot';
	import { useStore, useSvelteFlow } from '@xyflow/svelte';
	import type { BaseWorkerData } from './nodes/BaseWorkerNode.svelte';
	import { Tabs, Tooltip } from 'bits-ui';
	import { getNodeIconStyle } from '$lib/utils/defaults';
	import SideDropdownMenu from './SideDropdownMenu.svelte';
	import { openAssistant } from '$lib/stores/assistantStateStore.svelte';
	import { untrack } from 'svelte';
	import { findDataInputForAssistant } from '$lib/utils/nodeUtils';

	let {
		onExport,
		onExecute,
		onClearGraph,
		onImport,
		onConfigureLLMs,
		onSave,
		onLoad,
		onLoadJSON,
		graphName = '',
		onGraphNameChange = (name: string) => {}
	}: {
		onExport: () => void;
		onExecute: () => void;
		onClearGraph: () => void;
		onImport: () => void;
		onConfigureLLMs: () => void;
		onSave: () => void;
		onLoad: () => void;
		onLoadJSON: (data: string) => void;
		graphName: string;
		onGraphNameChange: (name: string) => void;
	} = $props();

	// Handles the start of dragging a new node
	function onDragStart(event: DragEvent, nodeType: string) {
		console.log('Drag started with node type:', nodeType);
		if (event.dataTransfer) {
			event.dataTransfer.setData('application/reactflow', nodeType);
			event.dataTransfer.effectAllowed = 'move';
		}
	}

	let isExecutionReady = $state(false);
	let isAssistantReady = $state(false);
	const { edges, nodes } = useStore();
	let { getNodes } = useSvelteFlow();

	// Selected tab value
	let selectedTab = $state('config');

	let unconnectedWorkersTooltip = $state<string | null>(null);
	let moduleLevelImportTooltip = $state<string | null>(null);
	let canAddModuleLevelImport = $state(true);
	// Define the types of nodes that are expected to have an output connection
	const workerNodeTypes = new Set([
		'datainput',
		'taskworker',
		'llmtaskworker',
		'joinedtaskworker',
		'subgraphworker',
		'chattaskworker',
		'datainput',
		'assistantinput'
	]);

	// Track the nodes to check if an assistant input node is present
	$effect(() => {
		const currentNodes = $nodes;
		untrack(() => {
			isAssistantReady = findDataInputForAssistant(currentNodes) !== null;
		});
	});

	$effect(() => {
		const currentNodes = $nodes;
		const hasModuleLevelImport =
			currentNodes.filter((node) => node.type === 'modulelevelimport').length > 0;
		// Be careful with triggering reactivity here in regards to the canAddModuleLevelImport state
		if (!hasModuleLevelImport == $state.snapshot(canAddModuleLevelImport)) {
			return;
		}
		if (hasModuleLevelImport) {
			canAddModuleLevelImport = false;
			moduleLevelImportTooltip =
				'A Module Level Import node already exists. You can only have one Module Level Import node.';
		} else {
			canAddModuleLevelImport = true;
			moduleLevelImportTooltip = null;
		}
	});

	$effect(() => {
		const currentNodes = $nodes;
		const currentEdges = $edges;

		const hasDataInput = currentNodes.filter((node) => node.type === 'datainput').length > 0;
		if (!hasDataInput) {
			isAssistantReady = false;
			unconnectedWorkersTooltip = 'No DataInput node found';
			return;
		}

		// Create a set of node IDs that are used as a source in any edge
		const sourceNodeIds = new Set(currentEdges.map((edge) => edge.source));

		let allRequiredOutputsConnected = true;
		const unconnectedNodes: string[] = [];

		// Filter nodes to find only those that are workers and have a defined type
		const relevantWorkerNodes = currentNodes.filter(
			(node) => node.type && workerNodeTypes.has(node.type)
		);

		// If there are worker nodes that require connections...
		if (relevantWorkerNodes.length > 0) {
			// ...check if each one is connected
			for (const node of relevantWorkerNodes) {
				// We know node.id is a string. Check if it's a source in any edge.
				if (!sourceNodeIds.has(node.id)) {
					allRequiredOutputsConnected = false;
					// Use label if available, otherwise fallback to ID
					unconnectedNodes.push((node.data as BaseWorkerData)?.workerName || node.id);
					// Don't break here, collect all unconnected nodes
				}
			}
		}

		// Determine if there are any nodes that actually require an output connection
		const workerNodesExist = relevantWorkerNodes.length > 0;

		// The graph is ready for execution if either:
		// 1. There are no worker nodes requiring an output connection.
		// 2. All worker nodes that require an output connection have one.
		isExecutionReady = !workerNodesExist || allRequiredOutputsConnected;

		// Update the tooltip based on the connection status
		if (!isExecutionReady && unconnectedNodes.length > 0) {
			unconnectedWorkersTooltip = `Outputs missing for: ${unconnectedNodes.join(', ')}`;
		} else {
			unconnectedWorkersTooltip = null; // Clear tooltip if ready or no specific nodes are missing connections
		}
	});

	// Function to handle Enter/Escape key press in the input
	function handleGraphNameKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault(); // Prevent potential form submission
			(event.target as HTMLElement)?.blur(); // Lose focus
		} else if (event.key === 'Escape') {
			(event.target as HTMLElement)?.blur(); // Lose focus
		}
	}
</script>

<div
	class="mb-1 flex items-stretch gap-4 rounded-md p-0 md:gap-6"
	data-testid="toolshelf-container"
>
	<!-- Examples Dropdown -->
	<div class="flex items-center border-r border-gray-300/70 pr-2">
		<SideDropdownMenu {onLoadJSON} />
	</div>

	<div class="flex min-w-[300px] flex-1 items-start gap-4">
		<!-- Draggable Nodes Section -->
		<div
			class="flex w-full flex-shrink-0 items-center gap-2 border-r border-gray-300/70 pr-4 md:w-1/3 lg:w-[30%]"
		>
			<div class="w-full">
				<Tooltip.Provider>
					<Tabs.Root value={selectedTab} class="w-full">
						<Tabs.List class="flex w-full rounded-md bg-gray-300/80 p-0.5 xl:p-1">
							<Tooltip.Root delayDuration={800}>
								<Tooltip.Trigger class="flex-1">
									<Tabs.Trigger
										value="config"
										class="flex-1 rounded-md px-2 py-1 text-xs font-medium transition-colors duration-150 data-[state=active]:bg-white data-[state=active]:shadow-sm xl:px-3 xl:py-1.5 xl:text-sm"
									>
										{#snippet child({ props }: { props: Record<string, unknown> })}
											<div {...props}>Configuration</div>
										{/snippet}
									</Tabs.Trigger>
								</Tooltip.Trigger>
								<Tooltip.Content
									class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
									side="bottom"
								>
									These nodes allow you to define PlanAI Task Types that can be used as the input
									and output types for workers.
								</Tooltip.Content>
							</Tooltip.Root>

							<Tooltip.Root delayDuration={800}>
								<Tooltip.Trigger class="flex-1">
									<Tabs.Trigger
										value="data"
										class="flex-1 rounded-md px-2 py-1 text-xs font-medium transition-colors duration-150 data-[state=active]:bg-white data-[state=active]:shadow-sm xl:px-3 xl:py-1.5 xl:text-sm"
									>
										{#snippet child({ props }: { props: Record<string, unknown> })}
											<div {...props}>Data</div>
										{/snippet}
									</Tabs.Trigger>
								</Tooltip.Trigger>
								<Tooltip.Content
									class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
									side="bottom"
								>
									These nodes allow you to inject data into a PlanAI Graph and retrieve its output.
								</Tooltip.Content>
							</Tooltip.Root>

							<Tooltip.Root delayDuration={800}>
								<Tooltip.Trigger class="flex-1">
									<Tabs.Trigger
										value="workers"
										class="flex-1 rounded-md px-2 py-1 text-xs font-medium transition-colors duration-150 data-[state=active]:bg-white data-[state=active]:shadow-sm xl:px-3 xl:py-1.5 xl:text-sm"
									>
										{#snippet child({ props }: { props: Record<string, unknown> })}
											<div {...props}>Workers</div>
										{/snippet}
									</Tabs.Trigger>
								</Tooltip.Trigger>
								<Tooltip.Content
									class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
									side="bottom"
								>
									Worker nodes process tasks and form the backbone of PlanAI. They include
									TaskWorkers for custom logic, LLMTaskWorkers for AI processing, JoinedTaskWorkers
									for combining multiple tasks, and more.
								</Tooltip.Content>
							</Tooltip.Root>
						</Tabs.List>

						<div class="min-h-[32px] pt-2">
							<Tabs.Content
								value="config"
								class="animate-in fade-in-50 flex flex-wrap gap-2 transition-all duration-200 ease-in-out"
							>
								<!-- Task Node -->
								{@const taskStyle = getNodeIconStyle('task')}
								<Tooltip.Root delayDuration={400}>
									<Tooltip.Trigger>
										<div
											class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-1.5 shadow-sm transition-shadow hover:shadow-md xl:p-2"
											role="button"
											tabindex="0"
											draggable="true"
											ondragstart={(e) => onDragStart(e, 'task')}
										>
											<div class="flex items-center gap-1 xl:gap-1.5">
												<taskStyle.icon size={14} weight="fill" class={taskStyle.color} />
												<div class="text-xs font-semibold xl:text-sm">Task</div>
											</div>
										</div>
									</Tooltip.Trigger>
									<Tooltip.Content
										class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
										side="bottom"
									>
										Define a PlanAI Task class that represents a specific data structure. Tasks are
										Pydantic models that flow through the graph as inputs and outputs.
									</Tooltip.Content>
								</Tooltip.Root>

								<!-- Task Import Node -->
								{@const taskImportStyle = getNodeIconStyle('taskimport')}
								<Tooltip.Root delayDuration={400}>
									<Tooltip.Trigger>
										<div
											class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-1.5 shadow-sm transition-shadow hover:shadow-md xl:p-2"
											role="button"
											tabindex="0"
											draggable="true"
											ondragstart={(e) => onDragStart(e, 'taskimport')}
										>
											<div class="flex items-center gap-1 xl:gap-1.5">
												<taskImportStyle.icon
													size={14}
													weight="fill"
													class={taskImportStyle.color}
												/>
												<div class="text-xs font-semibold xl:text-sm">Task Import</div>
											</div>
										</div>
									</Tooltip.Trigger>
									<Tooltip.Content
										class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
										side="bottom"
									>
										Import existing Task classes from Python modules to use in your workflow.
									</Tooltip.Content>
								</Tooltip.Root>

								<!-- Module Level Import Node -->
								{@const moduleLevelImportStyle = getNodeIconStyle('modulelevelimport')}
								<Tooltip.Root delayDuration={400}>
									<Tooltip.Trigger>
										<div
											class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 p-1.5 shadow-sm transition-shadow hover:shadow-md xl:p-2 {canAddModuleLevelImport
												? 'cursor-grab bg-white'
												: 'cursor-not-allowed opacity-50'}"
											role="button"
											tabindex="0"
											draggable={canAddModuleLevelImport}
											ondragstart={(e) => onDragStart(e, 'modulelevelimport')}
										>
											<div class="flex items-center gap-1 xl:gap-1.5">
												<moduleLevelImportStyle.icon
													size={14}
													weight="fill"
													class={moduleLevelImportStyle.color}
												/>
												<div class="text-xs font-semibold xl:text-sm">Module Imports</div>
											</div>
										</div>
									</Tooltip.Trigger>
									<Tooltip.Content
										class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
										side="bottom"
									>
										Import existing Python modules to use in your workflow.
										{#if moduleLevelImportTooltip}
											<span class="text-red-700">{moduleLevelImportTooltip}</span>
										{/if}
									</Tooltip.Content>
								</Tooltip.Root>

								<!-- Tool Node -->
								{@const toolNodeStyle = getNodeIconStyle('tool')}
								<Tooltip.Root delayDuration={400}>
									<Tooltip.Trigger>
										<div
											class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-1.5 shadow-sm transition-shadow hover:shadow-md xl:p-2"
											role="button"
											tabindex="0"
											draggable="true"
											ondragstart={(e) => onDragStart(e, 'tool')}
										>
											<div class="flex items-center gap-1 xl:gap-1.5">
												<toolNodeStyle.icon size={14} weight="fill" class={toolNodeStyle.color} />
												<div class="text-xs font-semibold xl:text-sm">Tool Library</div>
											</div>
										</div>
									</Tooltip.Trigger>
									<Tooltip.Content
										class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
										side="bottom"
									>
										A library node that provides a collection of tools that can be used for function
										calling by LLMs.
									</Tooltip.Content>
								</Tooltip.Root>
							</Tabs.Content>

							<Tabs.Content
								value="data"
								class="animate-in fade-in-50 flex flex-wrap gap-2 transition-all duration-200 ease-in-out"
							>
								<!-- DataInput Node -->
								{@const dataInputStyle = getNodeIconStyle('datainput')}
								<Tooltip.Root delayDuration={400}>
									<Tooltip.Trigger>
										<div
											class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-1.5 shadow-sm transition-shadow hover:shadow-md xl:p-2"
											role="button"
											tabindex="0"
											draggable="true"
											ondragstart={(e) => onDragStart(e, 'datainput')}
										>
											<div class="flex items-center gap-1 xl:gap-1.5">
												<dataInputStyle.icon size={14} weight="fill" class={dataInputStyle.color} />
												<div class="text-xs font-semibold xl:text-sm">DataInput</div>
											</div>
										</div>
									</Tooltip.Trigger>
									<Tooltip.Content
										class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
										side="bottom"
									>
										Create an entry point for your PlanAI Graph that allows data to be injected when
										executing the workflow.
									</Tooltip.Content>
								</Tooltip.Root>

								<!-- AssistantInput Node -->
								{@const assistantInputStyle = getNodeIconStyle('assistantinput')}
								<Tooltip.Root delayDuration={400}>
									<Tooltip.Trigger>
										<div
											class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-purple-50 p-1.5 shadow-sm transition-shadow hover:shadow-md xl:p-2"
											role="button"
											tabindex="0"
											draggable="true"
											ondragstart={(e) => onDragStart(e, 'assistantinput')}
										>
											<div class="flex items-center gap-1 xl:gap-1.5">
												<assistantInputStyle.icon
													size={14}
													weight="fill"
													class={assistantInputStyle.color}
												/>
												<div class="text-xs font-semibold xl:text-sm">AssistantInput</div>
											</div>
										</div>
									</Tooltip.Trigger>
									<Tooltip.Content
										class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
										side="bottom"
									>
										Provides a dedicated input node for the AI Assistant to interact with the graph.
									</Tooltip.Content>
								</Tooltip.Root>

								<!-- Data Output Node -->
								{@const dataOutputStyle = getNodeIconStyle('dataoutput')}
								<Tooltip.Root delayDuration={400}>
									<Tooltip.Trigger>
										<div
											class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-1.5 shadow-sm transition-shadow hover:shadow-md xl:p-2"
											role="button"
											tabindex="0"
											draggable="true"
											ondragstart={(e) => onDragStart(e, 'dataoutput')}
										>
											<div class="flex items-center gap-1 xl:gap-1.5">
												<dataOutputStyle.icon
													size={14}
													weight="fill"
													class={dataOutputStyle.color}
												/>
												<div class="text-xs font-semibold xl:text-sm">DataOutput</div>
											</div>
										</div>
									</Tooltip.Trigger>
									<Tooltip.Content
										class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
										side="bottom"
									>
										Create a sink for your PlanAI Graph that collects and displays results from the
										workflow execution.
									</Tooltip.Content>
								</Tooltip.Root>
							</Tabs.Content>

							<Tabs.Content
								value="workers"
								class="animate-in fade-in-50 flex flex-wrap gap-2 transition-all duration-200 ease-in-out"
							>
								<!-- TaskWorker Node -->
								{@const taskWorkerStyle = getNodeIconStyle('taskworker')}
								<Tooltip.Root delayDuration={400}>
									<Tooltip.Trigger>
										<div
											class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-1.5 shadow-sm transition-shadow hover:shadow-md xl:p-2"
											role="button"
											tabindex="0"
											draggable="true"
											ondragstart={(e) => onDragStart(e, 'taskworker')}
										>
											<div class="flex items-center gap-1 xl:gap-1.5">
												<taskWorkerStyle.icon
													size={14}
													weight="fill"
													class={taskWorkerStyle.color}
												/>
												<div class="text-xs font-semibold xl:text-sm">TaskWorker</div>
											</div>
										</div>
									</Tooltip.Trigger>
									<Tooltip.Content
										class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
										side="bottom"
									>
										A basic worker that processes tasks with custom Python logic. Implement the
										consume_work method to transform input tasks into output tasks.
									</Tooltip.Content>
								</Tooltip.Root>

								<!-- LLMTaskWorker Node -->
								{@const llmTaskWorkerStyle = getNodeIconStyle('llmtaskworker')}
								<Tooltip.Root delayDuration={400}>
									<Tooltip.Trigger>
										<div
											class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-1.5 shadow-sm transition-shadow hover:shadow-md xl:p-2"
											role="button"
											tabindex="0"
											draggable="true"
											ondragstart={(e) => onDragStart(e, 'llmtaskworker')}
										>
											<div class="flex items-center gap-1 xl:gap-1.5">
												<llmTaskWorkerStyle.icon
													size={14}
													weight="fill"
													class={llmTaskWorkerStyle.color}
												/>
												<div class="text-xs font-semibold xl:text-sm">LLMTaskWorker</div>
											</div>
										</div>
									</Tooltip.Trigger>
									<Tooltip.Content
										class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
										side="bottom"
									>
										Process tasks using Large Language Models (LLMs). Define prompts and handle
										AI-generated responses with validation and post-processing.
									</Tooltip.Content>
								</Tooltip.Root>

								<!-- JoinedTaskWorker Node -->
								{@const joinedTaskWorkerStyle = getNodeIconStyle('joinedtaskworker')}
								<Tooltip.Root delayDuration={400}>
									<Tooltip.Trigger>
										<div
											class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-1.5 shadow-sm transition-shadow hover:shadow-md xl:p-2"
											role="button"
											tabindex="0"
											draggable="true"
											ondragstart={(e) => onDragStart(e, 'joinedtaskworker')}
										>
											<div class="flex items-center gap-1 xl:gap-1.5">
												<joinedTaskWorkerStyle.icon
													size={14}
													weight="fill"
													class={joinedTaskWorkerStyle.color}
												/>
												<div class="text-xs font-semibold xl:text-sm">JoinedTaskWorker</div>
											</div>
										</div>
									</Tooltip.Trigger>
									<Tooltip.Content
										class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
										side="bottom"
									>
										Combine multiple related tasks into one process. Waits for all upstream tasks
										sharing a common ancestor to complete before processing them together.
									</Tooltip.Content>
								</Tooltip.Root>

								<!-- SubGraphWorker Node -->
								{@const subGraphWorkerStyle = getNodeIconStyle('subgraphworker')}
								<Tooltip.Root delayDuration={400}>
									<Tooltip.Trigger>
										<div
											class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-1.5 shadow-sm transition-shadow hover:shadow-md xl:p-2"
											role="button"
											tabindex="0"
											draggable="true"
											ondragstart={(e) => onDragStart(e, 'subgraphworker')}
										>
											<div class="flex items-center gap-1 xl:gap-1.5">
												<subGraphWorkerStyle.icon
													size={14}
													weight="fill"
													class={subGraphWorkerStyle.color}
												/>
												<div class="text-xs font-semibold xl:text-sm">SubGraphWorker</div>
											</div>
										</div>
									</Tooltip.Trigger>
									<Tooltip.Content
										class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
										side="bottom"
									>
										Encapsulate an entire PlanAI Graph as a single worker within a larger workflow.
										Useful for creating reusable, modular components.
									</Tooltip.Content>
								</Tooltip.Root>

								<!-- ChatTaskWorker Node -->
								{@const chatTaskWorkerStyle = getNodeIconStyle('chattaskworker')}
								<Tooltip.Root delayDuration={400}>
									<Tooltip.Trigger>
										<div
											class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-1.5 shadow-sm transition-shadow hover:shadow-md xl:p-2"
											role="button"
											tabindex="0"
											draggable="true"
											ondragstart={(e) => onDragStart(e, 'chattaskworker')}
										>
											<div class="flex items-center gap-1 xl:gap-1.5">
												<chatTaskWorkerStyle.icon
													size={14}
													weight="fill"
													class={chatTaskWorkerStyle.color}
												/>
												<div class="text-xs font-semibold xl:text-sm">ChatTaskWorker</div>
											</div>
										</div>
									</Tooltip.Trigger>
									<Tooltip.Content
										class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
										side="bottom"
									>
										Specialized worker for handling conversational AI tasks. Maintains chat history
										and manages interactive dialogues with LLMs.
									</Tooltip.Content>
								</Tooltip.Root>
							</Tabs.Content>
						</div>
					</Tabs.Root>
				</Tooltip.Provider>
			</div>
		</div>

		<!-- Actions Section -->
		<div class="flex min-w-0 shrink-[2] flex-col gap-2 border-r border-gray-300/70 pl-4 pr-4">
			<!-- Graph Name Input -->
			<div class="flex items-center gap-2">
				<label for="graph-name" class="text-xs uppercase tracking-wider text-gray-500"
					>Graph Name</label
				>
				<input
					id="graph-name"
					type="text"
					value={graphName}
					placeholder="Unnamed Graph"
					class="min-w-25 h-[30px] rounded-md border border-gray-300 px-2 text-xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 xl:h-[34px] xl:px-3 xl:text-sm"
					oninput={(e) => onGraphNameChange(e.currentTarget.value)}
					onkeydown={handleGraphNameKeydown}
				/>
			</div>

			<!-- Action Buttons -->
			<div class="flex min-w-0 flex-1 flex-wrap gap-2">
				<!-- Load Button -->
				<button
					onclick={onLoad}
					class="flex items-center rounded bg-teal-500 px-2 py-1 text-xs font-medium text-white shadow-sm transition-colors hover:bg-teal-600 xl:px-3 xl:py-1.5 xl:text-sm"
					title="Load graph from JSON file"
					data-testid="load-button"
				>
					<FolderOpen size={16} weight="bold" class="mr-1 xl:mr-1.5 xl:size-[18px]" />
					Load
				</button>
				<!-- Save Button -->
				<button
					onclick={onSave}
					class="flex items-center rounded bg-sky-500 px-2 py-1 text-xs font-medium text-white shadow-sm transition-colors hover:bg-sky-600 xl:px-3 xl:py-1.5 xl:text-sm"
					title="Save graph to JSON file"
					data-testid="save-button"
				>
					<FloppyDisk size={16} weight="bold" class="mr-1 xl:mr-1.5 xl:size-[18px]" />
					Save
				</button>
				<!-- Python Import Button -->
				<button
					onclick={onImport}
					class="flex items-center rounded bg-blue-500 px-2 py-1 text-xs font-medium text-white shadow-sm transition-colors hover:bg-blue-600 disabled:opacity-50 xl:px-3 xl:py-1.5 xl:text-sm"
					title="Import Task definitions from Python file"
					data-testid="import-button"
				>
					<UploadSimple size={16} weight="bold" class="mr-1 xl:mr-1.5 xl:size-[18px]" />
					Import
				</button>
				<!-- Export Button -->
				<button
					onclick={onExport}
					class="flex items-center rounded bg-orange-500 px-2 py-1 text-xs font-medium text-white shadow-sm transition-colors hover:bg-orange-600 xl:px-3 xl:py-1.5 xl:text-sm"
					data-testid="export-button"
					title={unconnectedWorkersTooltip ? unconnectedWorkersTooltip : 'Export'}
				>
					<Export size={16} class="mr-1 xl:mr-1.5 xl:size-[18px]" />
					Export
				</button>
				<!-- Execute Button -->
				<button
					onclick={onExecute}
					class="flex items-center rounded bg-green-600 px-2 py-1 text-xs font-medium text-white shadow-sm transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-green-600 xl:px-3 xl:py-1.5 xl:text-sm"
					data-testid="execute-button"
					disabled={!isExecutionReady}
					title={unconnectedWorkersTooltip ? unconnectedWorkersTooltip : 'Execute Graph'}
				>
					<Play size={16} class="mr-1 xl:mr-1.5 xl:size-[18px]" />
					Execute
				</button>
				<!-- Assistant Button -->
				<button
					onclick={openAssistant}
					class="flex items-center rounded bg-purple-600 px-2 py-1 text-xs font-medium text-white shadow-sm transition-colors hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-purple-600 xl:px-3 xl:py-1.5 xl:text-sm"
					title="Open AI Assistant"
					disabled={!isAssistantReady}
				>
					<Robot size={16} class="mr-1 xl:mr-1.5 xl:size-[18px]" />
					Assistant
				</button>
				<!-- Clear Button -->
				<button
					onclick={onClearGraph}
					class="flex items-center rounded bg-red-600 px-2 py-1 text-xs font-medium text-white shadow-sm transition-colors hover:bg-red-700 xl:px-3 xl:py-1.5 xl:text-sm"
					title="Clear the entire graph"
				>
					<Eraser size={16} class="mr-1 xl:mr-1.5 xl:size-[18px]" />
					Clear
				</button>
				<!-- Configure LLMs Button -->
				<button
					onclick={onConfigureLLMs}
					class="flex items-center rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 xl:px-3 xl:py-1.5 xl:text-sm"
					title="Configure LLM Models"
				>
					<Gear size={16} class="mr-1 xl:mr-1.5 xl:size-[18px]" />
					Configure LLMs
				</button>
			</div>
		</div>
	</div>

	<!-- Interpreter Section -->
	<div class="flex flex-none items-start gap-2">
		<div class="flex flex-col items-start gap-2">
			<span class="text-xs uppercase tracking-wider text-gray-500">Interpreter</span>
			<PythonInterpreterSelector />
		</div>
	</div>
</div>
