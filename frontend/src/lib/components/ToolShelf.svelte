<script lang="ts">
	import Robot from 'phosphor-svelte/lib/Robot';
	import Cube from 'phosphor-svelte/lib/Cube';
	import Brain from 'phosphor-svelte/lib/Brain';
	import ArrowsIn from 'phosphor-svelte/lib/ArrowsIn';
	import Chat from 'phosphor-svelte/lib/Chat';
	import FileMagnifyingGlass from 'phosphor-svelte/lib/FileMagnifyingGlass';
	import Eraser from 'phosphor-svelte/lib/Eraser';
	import UploadSimple from 'phosphor-svelte/lib/UploadSimple';
	import Network from 'phosphor-svelte/lib/Network';
	import PythonInterpreterSelector from '$lib/components/PythonInterpreterSelector.svelte';
	import Play from 'phosphor-svelte/lib/Play';
	import Gear from 'phosphor-svelte/lib/Gear';
	import Keyboard from 'phosphor-svelte/lib/Keyboard';
	import Table from 'phosphor-svelte/lib/Table';
	import FloppyDisk from 'phosphor-svelte/lib/FloppyDisk';
	import FolderOpen from 'phosphor-svelte/lib/FolderOpen';
	import { useStore } from '@xyflow/svelte';
	import type { BaseWorkerData } from './nodes/BaseWorkerNode.svelte';
	import { Tabs, Tooltip } from 'bits-ui';

	let {
		onExport,
		onClearGraph,
		onImport,
		onConfigureLLMs,
		onSave,
		onLoad
	}: {
		onExport: () => void;
		onClearGraph: () => void;
		onImport: () => void;
		onConfigureLLMs: () => void;
		onSave: () => void;
		onLoad: () => void;
	} = $props<{
		onExport: () => void;
		onClearGraph: () => void;
		onImport: () => void;
		onConfigureLLMs: () => void;
		onSave: () => void;
		onLoad: () => void;
	}>();

	// Handles the start of dragging a new node
	function onDragStart(event: DragEvent, nodeType: string) {
		console.log('Drag started with node type:', nodeType);
		if (event.dataTransfer) {
			event.dataTransfer.setData('application/reactflow', nodeType);
			event.dataTransfer.effectAllowed = 'move';
		}
	}

	let isExecutionReady = $state(false);
	const { edges, nodes } = useStore();

	// Selected tab value
	let selectedTab = $state('tasks');

	let unconnectedWorkersTooltip = $state<string | null>(null);

	// Define the types of nodes that are expected to have an output connection
	const workerNodeTypes = new Set([
		'datainput',
		'taskworker',
		'llmtaskworker',
		'joinedtaskworker',
		'subgraphworker',
		'chattaskworker'
	]);

	$effect(() => {
		const currentNodes = $nodes;
		const currentEdges = $edges;

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
		} else {
			// If there are no worker nodes requiring output, then technically all required outputs *are* connected.
			allRequiredOutputsConnected = true;
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
</script>

<div
	class="mb-1 flex flex-wrap items-stretch gap-4 rounded-md p-0 md:gap-6"
	data-testid="toolshelf-container"
>
	<!-- Draggable Nodes Section -->
	<div class="flex min-w-[300px] flex-1 items-center gap-2 border-r border-gray-300/70 pr-4">
		<div class="w-full md:w-auto">
			<Tooltip.Provider>
				<Tabs.Root value={selectedTab} class="w-full">
					<Tabs.List class="flex w-[300px] rounded-md bg-gray-300/80 p-1">
						<Tooltip.Root delayDuration={400}>
							<Tooltip.Trigger asChild>
								<Tabs.Trigger
									value="tasks"
									class="flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-150 data-[state=active]:bg-white data-[state=active]:shadow-sm"
								>
									Tasks
								</Tabs.Trigger>
							</Tooltip.Trigger>
							<Tooltip.Content
								class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
								side="bottom"
							>
								These nodes allow you to define PlanAI Task Types that can be used as the input and
								output types for workers.
							</Tooltip.Content>
						</Tooltip.Root>

						<Tooltip.Root delayDuration={400}>
							<Tooltip.Trigger asChild>
								<Tabs.Trigger
									value="data"
									class="flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-150 data-[state=active]:bg-white data-[state=active]:shadow-sm"
								>
									Data
								</Tabs.Trigger>
							</Tooltip.Trigger>
							<Tooltip.Content
								class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
								side="bottom"
							>
								These nodes allow you to inject data into a PlanAI Graph and retrieve its output.
							</Tooltip.Content>
						</Tooltip.Root>

						<Tooltip.Root delayDuration={400}>
							<Tooltip.Trigger asChild>
								<Tabs.Trigger
									value="workers"
									class="flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-150 data-[state=active]:bg-white data-[state=active]:shadow-sm"
								>
									Workers
								</Tabs.Trigger>
							</Tooltip.Trigger>
							<Tooltip.Content
								class="z-50 max-w-xs rounded-md border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-800 shadow-md"
								side="bottom"
							>
								Worker nodes process tasks and form the backbone of PlanAI. They include TaskWorkers
								for custom logic, LLMTaskWorkers for AI processing, JoinedTaskWorkers for combining
								multiple tasks, and more.
							</Tooltip.Content>
						</Tooltip.Root>
					</Tabs.List>

					<div class="min-h-[32px] overflow-x-auto pt-2">
						<Tabs.Content
							value="tasks"
							class="animate-in fade-in-50 flex flex-wrap gap-2 transition-all duration-200 ease-in-out md:flex-nowrap"
						>
							<!-- Task Node -->
							<Tooltip.Root delayDuration={400}>
								<Tooltip.Trigger>
									<div
										class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
										role="button"
										tabindex="0"
										draggable="true"
										ondragstart={(e) => onDragStart(e, 'task')}
									>
										<div class="flex items-center gap-1.5">
											<Cube size={16} weight="fill" class="text-blue-500" />
											<div class="text-sm font-semibold">Task</div>
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
							<Tooltip.Root delayDuration={400}>
								<Tooltip.Trigger>
									<div
										class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
										role="button"
										tabindex="0"
										draggable="true"
										ondragstart={(e) => onDragStart(e, 'taskimport')}
									>
										<div class="flex items-center gap-1.5">
											<FileMagnifyingGlass size={16} weight="fill" class="text-cyan-500" />
											<div class="text-sm font-semibold">TaskImport</div>
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
						</Tabs.Content>

						<Tabs.Content
							value="data"
							class="animate-in fade-in-50 flex flex-wrap gap-2 transition-all duration-200 ease-in-out md:flex-nowrap"
						>
							<!-- DataInput Node -->
							<Tooltip.Root delayDuration={400}>
								<Tooltip.Trigger>
									<div
										class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
										role="button"
										tabindex="0"
										draggable="true"
										ondragstart={(e) => onDragStart(e, 'datainput')}
									>
										<div class="flex items-center gap-1.5">
											<Keyboard size={16} weight="fill" class="text-gray-500" />
											<div class="text-sm font-semibold">DataInput</div>
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

							<!-- Data Output Node -->
							<Tooltip.Root delayDuration={400}>
								<Tooltip.Trigger>
									<div
										class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
										role="button"
										tabindex="0"
										draggable="true"
										ondragstart={(e) => onDragStart(e, 'dataoutput')}
									>
										<div class="flex items-center gap-1.5">
											<Table size={16} weight="fill" class="text-pink-500" />
											<div class="text-sm font-semibold">DataOutput</div>
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
							class="animate-in fade-in-50 flex flex-wrap gap-2 transition-all duration-200 ease-in-out md:flex-nowrap"
						>
							<!-- TaskWorker Node -->
							<Tooltip.Root delayDuration={400}>
								<Tooltip.Trigger>
									<div
										class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
										role="button"
										tabindex="0"
										draggable="true"
										ondragstart={(e) => onDragStart(e, 'taskworker')}
									>
										<div class="flex items-center gap-1.5">
											<Robot size={16} weight="fill" class="text-purple-500" />
											<div class="text-sm font-semibold">TaskWorker</div>
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
							<Tooltip.Root delayDuration={400}>
								<Tooltip.Trigger>
									<div
										class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
										role="button"
										tabindex="0"
										draggable="true"
										ondragstart={(e) => onDragStart(e, 'llmtaskworker')}
									>
										<div class="flex items-center gap-1.5">
											<Brain size={16} weight="fill" class="text-green-500" />
											<div class="text-sm font-semibold">LLMTaskWorker</div>
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
							<Tooltip.Root delayDuration={400}>
								<Tooltip.Trigger>
									<div
										class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
										role="button"
										tabindex="0"
										draggable="true"
										ondragstart={(e) => onDragStart(e, 'joinedtaskworker')}
									>
										<div class="flex items-center gap-1.5">
											<ArrowsIn size={16} weight="fill" class="text-orange-500" />
											<div class="text-sm font-semibold">JoinedTaskWorker</div>
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
							<Tooltip.Root delayDuration={400}>
								<Tooltip.Trigger>
									<div
										class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
										role="button"
										tabindex="0"
										draggable="true"
										ondragstart={(e) => onDragStart(e, 'subgraphworker')}
									>
										<div class="flex items-center gap-1.5">
											<Network size={16} weight="fill" class="text-teal-500" />
											<div class="text-sm font-semibold">SubGraphWorker</div>
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
							<Tooltip.Root delayDuration={400}>
								<Tooltip.Trigger>
									<div
										class="flex-shrink-0 cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
										role="button"
										tabindex="0"
										draggable="true"
										ondragstart={(e) => onDragStart(e, 'chattaskworker')}
									>
										<div class="flex items-center gap-1.5">
											<Chat size={16} weight="fill" class="text-red-500" />
											<div class="text-sm font-semibold">ChatTaskWorker</div>
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
	<div class="flex items-center gap-2 border-r border-gray-300/70 pr-4">
		<div class="flex flex-wrap gap-2">
			<!-- Load Button -->
			<button
				onclick={onLoad}
				class="flex items-center rounded bg-teal-500 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-600"
				title="Load graph from JSON file"
				data-testid="load-button"
			>
				<FolderOpen size={18} weight="bold" class="mr-1.5" />
				Load
			</button>
			<!-- Save Button -->
			<button
				onclick={onSave}
				class="flex items-center rounded bg-sky-500 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-sky-600"
				title="Save graph to JSON file"
				data-testid="save-button"
			>
				<FloppyDisk size={18} weight="bold" class="mr-1.5" />
				Save
			</button>
			<!-- Python Import Button -->
			<button
				onclick={onImport}
				class="flex items-center rounded bg-blue-500 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-600 disabled:opacity-50"
				title="Import Task definitions from Python file"
				data-testid="import-button"
			>
				<UploadSimple size={18} weight="bold" class="mr-1.5" />
				Import
			</button>
			<!-- Execute Button -->
			<button
				onclick={onExport}
				class="flex items-center rounded bg-green-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-green-600"
				data-testid="execute-button"
				disabled={!isExecutionReady}
				title={unconnectedWorkersTooltip ? unconnectedWorkersTooltip : 'Execute Graph'}
			>
				<Play size={18} class="mr-1.5" />
				Execute
			</button>
			<!-- Clear Button -->
			<button
				onclick={onClearGraph}
				class="flex items-center rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-red-700"
				title="Clear the entire graph"
			>
				<Eraser size={18} class="mr-1.5" />
				Clear
			</button>
			<!-- Configure LLMs Button -->
			<button
				onclick={onConfigureLLMs}
				class="flex items-center rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700"
				title="Configure LLM Models"
			>
				<Gear size={18} class="mr-1.5" />
				Configure LLMs
			</button>
		</div>
	</div>

	<!-- Interpreter Section -->
	<div class="flex items-center gap-2">
		<span class="text-xs uppercase tracking-wider text-gray-500">Interpreter</span>
		<PythonInterpreterSelector />
	</div>
</div>
