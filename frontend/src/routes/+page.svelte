<script lang="ts">
	import { SvelteFlow, Background, Controls } from '@xyflow/svelte';
	import type { Node, Edge } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import ToolShelf from '$lib/components/ToolShelf.svelte';
	import TaskNode from '$lib/components/nodes/TaskNode.svelte';
	import { writable } from 'svelte/store';
	import { allClassNames } from '$lib/stores/classNameStore';
	import ContextMenu from '$lib/components/ContextMenu.svelte';

	// Define node types with props for each node type
	const nodeTypes: any = {
		task: TaskNode
	};

	// Use Svelte stores for nodes and edges as required by @xyflow/svelte
	const nodes = writable<Node[]>([]);
	const edges = writable<Edge[]>([]);

	// Context menu state
	let showContextMenu = $state(false);
	let contextMenuX = $state(0);
	let contextMenuY = $state(0);
	let contextMenuNode = $state<Node | null>(null);

	// When nodes change, update the class name map
	$effect(() => {
		let classNameMap = new Map<string, string>();

		// Subscribe to get current nodes
		const unsubNodes = nodes.subscribe((currentNodes) => {
			// Reset the map
			classNameMap = new Map();

			// Add each node's class name with its ID
			currentNodes.forEach((node) => {
				if (node.data?.className && typeof node.data.className === 'string') {
					classNameMap.set(node.id, node.data.className);
				}
			});

			// Update the store
			allClassNames.set(classNameMap);
		});

		return unsubNodes;
	});

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

		// Generate a unique class name
		let uniqueClassName = 'Task';
		let counter = 1;
		let classNameMap = new Map<string, string>();

		// Get current class names
		const unsubscribe = allClassNames.subscribe((map) => {
			classNameMap = map;
		});
		unsubscribe();

		// Get all existing class names
		const existingNames = new Set(classNameMap.values());

		// Make sure the class name is unique
		while (existingNames.has(uniqueClassName)) {
			uniqueClassName = `Task${counter}`;
			counter++;
		}

		// Create a new node object with explicit fields array
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
				className: uniqueClassName,
				fields: [], // Explicitly initialized empty array
				nodeId: id // Pass the node ID for validation
			}
		};

		// Update our nodes store
		nodes.update((currentNodes) => {
			return [...currentNodes, newNode];
		});
	}

	function onDragOver(event: DragEvent) {
		event.preventDefault();
		event.dataTransfer!.dropEffect = 'move';
	}

	// Handle node context menu
	function handleNodeContextMenu(event: MouseEvent, node: any) {
		// Prevent the default context menu
		event.preventDefault();

		// Set the context menu position and node
		contextMenuX = event.clientX;
		contextMenuY = event.clientY;
		contextMenuNode = node;
		showContextMenu = true;
	}

	// Close the context menu
	function closeContextMenu() {
		showContextMenu = false;
		contextMenuNode = null;
	}

	// Delete the selected node
	function deleteNode() {
		if (!contextMenuNode) return;

		nodes.update((currentNodes) => currentNodes.filter((node) => node.id !== contextMenuNode!.id));

		// Remove any connected edges
		edges.update((currentEdges) =>
			currentEdges.filter(
				(edge) => edge.source !== contextMenuNode!.id && edge.target !== contextMenuNode!.id
			)
		);

		// Close the context menu
		closeContextMenu();
	}

	// Context menu items
	const getContextMenuItems = () => [
		{
			label: 'Delete Node',
			icon: '🗑️',
			action: deleteNode,
			danger: true
		}
	];

	// Handle pane click to close context menu
	function onPaneClick() {
		if (showContextMenu) {
			closeContextMenu();
		}
	}
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
			onclick={onPaneClick}
			class="flex-grow"
			fitView
			nodesDraggable
			proOptions={{ hideAttribution: true }}
			on:nodecontextmenu={({ detail: { event, node } }) => {
				if ('clientX' in event) {
					// Check if it's a MouseEvent
					handleNodeContextMenu(event, node);
				}
			}}
		>
			<Background />
			<Controls />
		</SvelteFlow>

		{#if showContextMenu}
			<ContextMenu
				items={getContextMenuItems()}
				x={contextMenuX}
				y={contextMenuY}
				onClose={closeContextMenu}
			/>
		{/if}
	</div>
</div>
