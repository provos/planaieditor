<script lang="ts">
	import Robot from 'phosphor-svelte/lib/Robot';
	import RobotSimple from 'phosphor-svelte/lib/Cube';
	import Cube from 'phosphor-svelte/lib/Cube';
	import Brain from 'phosphor-svelte/lib/Brain';
	import ArrowsIn from 'phosphor-svelte/lib/ArrowsIn';

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
</div>
