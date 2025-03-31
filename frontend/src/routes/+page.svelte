<script lang="ts">
	import { SvelteFlow, Background, Controls } from '@xyflow/svelte';
	import type { Node, Edge } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import ToolShelf from '$lib/components/ToolShelf.svelte';
	import TaskNode from '$lib/components/nodes/TaskNode.svelte';
	import { writable } from 'svelte/store';

	// Define node types - use any type to bypass type compatibility issues
	const nodeTypes: any = {
		task: TaskNode
	};

	// Initial empty nodes and edges as stores for SvelteFlow
	const nodesStore = writable<Node[]>([]);
	const edgesStore = writable<Edge[]>([]);

	// Process drag and drop of new nodes
	function onDrop(event: DragEvent) {
		event.preventDefault();

		const nodeType = event.dataTransfer?.getData('application/reactflow');

		if (!nodeType) return;

		// Get the position where the node is dropped
		const flowBounds = document.querySelector('.react-flow')?.getBoundingClientRect();
		if (!flowBounds) return;

		const position = {
			x: event.clientX - flowBounds.left,
			y: event.clientY - flowBounds.top
		};

		// Create a unique ID for the new node
		const id = `${nodeType}-${Date.now()}`;

		// Create a new node object
		const newNode = {
			id,
			type: nodeType,
			position,
			draggable: true,
			selectable: true,
			deletable: true,
			selected: false,
			dragging: false,
			zIndex: 0,
			data: {
				className: 'NewTask',
				fields: []
			}
		};

		// Update our store
		nodesStore.update((nodes) => [...nodes, newNode]);
	}

	function onDragOver(event: DragEvent) {
		event.preventDefault();
		event.dataTransfer!.dropEffect = 'move';
	}
</script>

<div class="flex h-screen w-screen flex-col">
	<div class="w-full border-b border-gray-300 bg-gray-100 p-4">
		<ToolShelf />
	</div>

	<div class="flex-grow">
		<SvelteFlow
			nodes={nodesStore}
			edges={edgesStore}
			{nodeTypes}
			on:drop={onDrop}
			on:dragover={onDragOver}
			class="flex-grow"
			fitView
		>
			<Background />
			<Controls />
		</SvelteFlow>
	</div>
</div>
