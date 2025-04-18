<script lang="ts">
	import Robot from 'phosphor-svelte/lib/Robot';
	import Cube from 'phosphor-svelte/lib/Cube';
	import Brain from 'phosphor-svelte/lib/Brain';
	import ArrowsIn from 'phosphor-svelte/lib/ArrowsIn';
	import FileCode from 'phosphor-svelte/lib/FileCode';
	import FileMagnifyingGlass from 'phosphor-svelte/lib/FileMagnifyingGlass';
	import Eraser from 'phosphor-svelte/lib/Eraser';
	import UploadSimple from 'phosphor-svelte/lib/UploadSimple';
	import PythonInterpreterSelector from '$lib/components/PythonInterpreterSelector.svelte';

	let {
		onExport,
		onClearGraph,
		onImport
	}: {
		onExport: () => void;
		onClearGraph: () => void;
		onImport: () => void;
	} = $props<{
		onExport: () => void;
		onClearGraph: () => void;
		onImport: () => void;
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

<div class="flex gap-4">
	<div class="text-lg font-bold">Tasks:</div>

	<div
		class="cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-md transition-shadow hover:shadow-lg"
		role="button"
		tabindex="0"
		draggable="true"
		ondragstart={(e) => onDragStart(e, 'task')}
		ondragend={() => console.log('Drag ended')}
	>
		<div class="flex items-center gap-1.5">
			<Cube size={16} weight="fill" class="text-blue-500" />
			<div class="text-sm font-semibold">Task</div>
		</div>
		<div class="text-xs text-gray-500">Data Model</div>
	</div>

	<div
		class="cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-md transition-shadow hover:shadow-lg"
		role="button"
		tabindex="0"
		draggable="true"
		ondragstart={(e) => onDragStart(e, 'taskimport')}
		ondragend={() => console.log('Drag ended')}
	>
		<div class="flex items-center gap-1.5">
			<FileMagnifyingGlass size={16} weight="fill" class="text-cyan-500" />
			<div class="text-sm font-semibold">TaskImport</div>
		</div>
		<div class="text-xs text-gray-500">Import Task</div>
	</div>

	<div class="text-lg font-bold">Workers:</div>

	<div
		class="cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-md transition-shadow hover:shadow-lg"
		role="button"
		tabindex="0"
		draggable="true"
		ondragstart={(e) => onDragStart(e, 'taskworker')}
		ondragend={() => console.log('Drag ended')}
	>
		<div class="flex items-center gap-1.5">
			<Robot size={16} weight="fill" class="text-purple-500" />
			<div class="text-sm font-semibold">TaskWorker</div>
		</div>
		<div class="text-xs text-gray-500">Basic Worker</div>
	</div>

	<div
		class="cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-md transition-shadow hover:shadow-lg"
		role="button"
		tabindex="0"
		draggable="true"
		ondragstart={(e) => onDragStart(e, 'llmtaskworker')}
		ondragend={() => console.log('Drag ended')}
	>
		<div class="flex items-center gap-1.5">
			<Brain size={16} weight="fill" class="text-green-500" />
			<div class="text-sm font-semibold">LLMTaskWorker</div>
		</div>
		<div class="text-xs text-gray-500">LLM-powered Worker</div>
	</div>

	<div
		class="cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-md transition-shadow hover:shadow-lg"
		role="button"
		tabindex="0"
		draggable="true"
		ondragstart={(e) => onDragStart(e, 'joinedtaskworker')}
		ondragend={() => console.log('Drag ended')}
	>
		<div class="flex items-center gap-1.5">
			<ArrowsIn size={16} weight="fill" class="text-orange-500" />
			<div class="text-sm font-semibold">JoinedTaskWorker</div>
		</div>
		<div class="text-xs text-gray-500">Multi-input Worker</div>
	</div>

	<div class="flex items-center">
		<button
			onclick={onImport}
			class="flex items-center rounded bg-blue-500 px-2 py-1 text-sm text-white hover:bg-blue-600 disabled:opacity-50"
			title="Import Task definitions from Python file"
		>
			<UploadSimple size={16} weight="bold" class="mr-1" />
			Import Python
		</button>
	</div>

	<div class="flex items-center">
		<PythonInterpreterSelector />
	</div>

	<div class="flex items-center">
		<button
			onclick={onExport}
			class="flex items-center rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
		>
			<FileCode size={18} class="mr-1.5" />
			Export to Python
		</button>
	</div>
	<div class="flex items-center">
		<button
			onclick={onClearGraph}
			class="flex items-center rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-red-700"
			title="Clear the entire graph"
		>
			<Eraser size={18} class="mr-1.5" />
			Clear Graph
		</button>
	</div>
</div>
