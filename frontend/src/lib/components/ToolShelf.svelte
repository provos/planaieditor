<script lang="ts">
	import Robot from 'phosphor-svelte/lib/Robot';
	import Cube from 'phosphor-svelte/lib/Cube';
	import Brain from 'phosphor-svelte/lib/Brain';
	import ArrowsIn from 'phosphor-svelte/lib/ArrowsIn';
	import FileCode from 'phosphor-svelte/lib/FileCode';
	import FileMagnifyingGlass from 'phosphor-svelte/lib/FileMagnifyingGlass';
	import Eraser from 'phosphor-svelte/lib/Eraser';
	import UploadSimple from 'phosphor-svelte/lib/UploadSimple';
	import Network from 'phosphor-svelte/lib/Network';
	import PythonInterpreterSelector from '$lib/components/PythonInterpreterSelector.svelte';
	import Export from 'phosphor-svelte/lib/Export';
	import Gear from 'phosphor-svelte/lib/Gear';

	let {
		onExport,
		onClearGraph,
		onImport,
		onConfigureLLMs
	}: {
		onExport: () => void;
		onClearGraph: () => void;
		onImport: () => void;
		onConfigureLLMs: () => void;
	} = $props<{
		onExport: () => void;
		onClearGraph: () => void;
		onImport: () => void;
		onConfigureLLMs: () => void;
	}>();

	// Handles the start of dragging a new node
	function onDragStart(event: DragEvent, nodeType: string) {
		console.log('Drag started with node type:', nodeType);
		if (event.dataTransfer) {
			event.dataTransfer.setData('application/reactflow', nodeType);
			event.dataTransfer.effectAllowed = 'move';
		}
	}
</script>

<div class="flex items-center gap-4">
	<!-- Draggable Nodes Section -->
	<div class="flex items-center gap-2 border-r border-gray-300 pr-4">
		<span class="font-semibold">Nodes:</span>
		<!-- Task Node -->
		<div
			class="cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
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
		<!-- Task Import Node -->
		<div
			class="cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
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
		<!-- TaskWorker Node -->
		<div
			class="cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
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
		<!-- LLMTaskWorker Node -->
		<div
			class="cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
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
		<!-- JoinedTaskWorker Node -->
		<div
			class="cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
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
		<!-- SubGraphWorker Node -->
		<div
			class="cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-sm transition-shadow hover:shadow-md"
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
	</div>

	<!-- Actions Section -->
	<div class="flex items-center gap-2 border-r border-gray-300 pr-4">
		<span class="font-semibold">Actions:</span>
		<!-- Import Button -->
		<button
			onclick={onImport}
			class="flex items-center rounded bg-blue-500 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-600 disabled:opacity-50"
			title="Import Task definitions from Python file"
		>
			<UploadSimple size={18} weight="bold" class="mr-1.5" />
			Import
		</button>
		<!-- Export Button -->
		<button
			onclick={onExport}
			class="flex items-center rounded bg-green-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-green-700"
		>
			<Export size={18} class="mr-1.5" />
			Export
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

	<!-- Interpreter Section -->
	<div class="flex items-center gap-2">
		<span class="font-semibold">Interpreter:</span>
		<PythonInterpreterSelector />
	</div>
</div>
