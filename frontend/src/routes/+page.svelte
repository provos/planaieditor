<script lang="ts">
	import { SvelteFlow, Background, Controls } from '@xyflow/svelte';
	import type { Node, Edge } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import ToolShelf from '$lib/components/ToolShelf.svelte';
	import TaskNode from '$lib/components/nodes/TaskNode.svelte';
	import { writable } from 'svelte/store';

	// Define node types
	const nodeTypes: any = {
		task: TaskNode
	};

	// Use Svelte stores for nodes and edges as required by @xyflow/svelte
	const nodes = writable<Node[]>([]);
	const edges = writable<Edge[]>([]);

	// Process drag and drop of new nodes
	function onDrop(event: DragEvent) {
		event.preventDefault();

		const nodeType = event.dataTransfer?.getData('application/reactflow');

		if (!nodeType) {
			console.log('No node type found in drag data');
			return;
		}

		// Get the position where the node is dropped
		const wrapper = document.querySelector('.svelte-flow__pane');
		const wrapperBounds = wrapper?.getBoundingClientRect();

		if (!wrapperBounds) {
			console.log('Could not find flow wrapper element');
			return;
		}

		const position = {
			x: event.clientX - wrapperBounds.left,
			y: event.clientY - wrapperBounds.top
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

		// Update our nodes store
		nodes.update((currentNodes) => {
			console.log('Adding node to store:', newNode);
			return [...currentNodes, newNode];
		});
	}

	function onDragOver(event: DragEvent) {
		event.preventDefault();
		event.dataTransfer!.dropEffect = 'move';
	}

	// For debugging
	$effect(() => {
		const unsubscribe = nodes.subscribe((currentNodes) => {
			console.log('Current nodes:', currentNodes);
		});

		return unsubscribe;
	});
</script>

<div class="flex h-screen w-screen flex-col">
	<div class="w-full border-b border-gray-300 bg-gray-100 p-4">
		<ToolShelf />
	</div>

	<div class="flex-grow">
		<SvelteFlow
			{nodes}
			{edges}
			{nodeTypes}
			ondrop={onDrop}
			ondragover={onDragOver}
			class="flex-grow"
			fitView
		>
			<Background />
			<Controls />
		</SvelteFlow>
	</div>
</div>
