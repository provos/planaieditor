<script lang="ts">
	import { SvelteFlow, Background, Controls } from '@xyflow/svelte';
	import type { Node, Edge } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import ToolShelf from '$lib/components/ToolShelf.svelte';
	import TaskNode from '$lib/components/nodes/TaskNode.svelte';
	import TaskWorkerNode from '$lib/components/nodes/TaskWorkerNode.svelte';
	import LLMTaskWorkerNode from '$lib/components/nodes/LLMTaskWorkerNode.svelte';
	import JoinedTaskWorkerNode from '$lib/components/nodes/JoinedTaskWorkerNode.svelte';
	import { writable } from 'svelte/store';
	import { allClassNames } from '$lib/stores/classNameStore';
	import ContextMenu from '$lib/components/ContextMenu.svelte';
	import type { ContextMenuItem } from '$lib/components/ContextMenu.svelte';
	import Trash from 'phosphor-svelte/lib/Trash';
	import Scissors from 'phosphor-svelte/lib/Scissors';
	import { io, Socket } from 'socket.io-client';
	import { onMount } from 'svelte';

	// Define node types and pass stores as props
	const nodeTypes: any = {
		task: TaskNode,
		taskworker: TaskWorkerNode,
		llmtaskworker: LLMTaskWorkerNode,
		joinedtaskworker: JoinedTaskWorkerNode
	};

	// Use Svelte stores for nodes and edges as required by @xyflow/svelte
	const nodes = writable<Node[]>([]);
	const edges = writable<Edge[]>([]);

	// Socket.IO connection state
	let socket: Socket | null = null;
	let isConnected = $state(false);
	let exportStatus = $state<{ type: 'idle' | 'loading' | 'success' | 'error'; message: string }>({
		type: 'idle',
		message: ''
	});

	onMount(() => {
		// Connect to the backend Socket.IO server
		socket = io('http://localhost:5001'); // Ensure this matches your backend port

		socket.on('connect', () => {
			console.log('Connected to backend:', socket?.id);
			isConnected = true;
		});

		socket.on('disconnect', () => {
			console.log('Disconnected from backend');
			isConnected = false;
			exportStatus = { type: 'idle', message: '' }; // Reset status on disconnect
		});

		socket.on('connect_error', (err) => {
			console.error('Connection error:', err);
			isConnected = false;
			exportStatus = { type: 'error', message: `Connection failed: ${err.message}` };
		});

		// Listen for export results from the backend
		socket.on('export_result', (data: { success: boolean; message?: string; error?: string }) => {
			if (data.success) {
				exportStatus = { type: 'success', message: data.message || 'Export successful!' };
				console.log('Export successful:', data.message);
			} else {
				exportStatus = { type: 'error', message: data.error || 'Export failed.' };
				console.error('Export failed:', data.error);
			}
		});

		return () => {
			// Disconnect the socket when the component is destroyed
			socket?.disconnect();
		};
	});

	// Context menu state
	let showContextMenu = $state(false);
	let contextMenuX = $state(0);
	let contextMenuY = $state(0);
	let contextMenuNode = $state<Node | null>(null);
	let contextMenuEdge = $state<Edge | null>(null);

	// When nodes change, update the class name map
	$effect(() => {
		let nameMap = new Map<string, string>();

		// Subscribe to get current nodes
		const unsubNodes = nodes.subscribe((currentNodes) => {
			// Reset the map
			nameMap = new Map();

			// Add each node's class name or worker name with its ID
			currentNodes.forEach((node) => {
				const name = node.data?.className || node.data?.workerName;
				if (name && typeof name === 'string') {
					nameMap.set(node.id, name);
				}
			});

			// Update the store
			allClassNames.set(nameMap);
		});

		return unsubNodes;
	});

	// Helper to generate unique node names
	function generateUniqueName(baseName: string, existingNames: Set<string>): string {
		let counter = 1;
		let uniqueName = `${baseName}${counter}`;
		while (existingNames.has(uniqueName)) {
			counter++;
			uniqueName = `${baseName}${counter}`;
		}
		return uniqueName;
	}

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

		// Configure node data based on node type
		let nodeData: any = {};

		// Get current existing names
		let currentNameMap = new Map<string, string>();
		const unsubscribeNames = allClassNames.subscribe((map) => {
			currentNameMap = map;
		});
		unsubscribeNames();
		const existingNames = new Set(currentNameMap.values());

		switch (nodeType) {
			case 'task': {
				const baseName = 'Task';
				const uniqueName = generateUniqueName(baseName, existingNames);
				nodeData = {
					className: uniqueName,
					fields: [],
					nodeId: id
				};
				break;
			}
			case 'taskworker': {
				const baseName = 'TaskWorker'; // Use base name for uniqueness check
				const uniqueName = generateUniqueName(baseName, existingNames);
				nodeData = {
					workerName: uniqueName, // Assign the unique name
					inputTypes: [],
					outputTypes: [],
					consumeWork: `def consume_work(self, task):
    # Process the input task and produce output
    # self.publish_work(output_task, input_task=task)
    pass`,
					nodeId: id
				};
				break;
			}
			case 'llmtaskworker': {
				const baseName = 'LLMTaskWorker';
				const uniqueName = generateUniqueName(baseName, existingNames);
				nodeData = {
					workerName: uniqueName, // Assign the unique name
					inputTypes: [],
					outputTypes: [],
					prompt: `# Process the task using an LLM
Analyze the following information and provide a response.`,
					systemPrompt: `You are a helpful task processing assistant.`,
					nodeId: id
				};
				break;
			}
			case 'joinedtaskworker': {
				const baseName = 'JoinedTaskWorker';
				const uniqueName = generateUniqueName(baseName, existingNames);
				nodeData = {
					workerName: uniqueName, // Assign the unique name
					inputTypes: [],
					outputTypes: [],
					consumeWork: `def consume_work(self, task):
    # Process the input task and produce output
    
    pass`,
					joinMethod: 'merge',
					nodeId: id
				};
				break;
			}
			default:
				console.log(`Unknown node type: ${nodeType}`);
				return;
		}

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
			data: nodeData
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
		event.preventDefault();
		contextMenuX = event.clientX;
		contextMenuY = event.clientY;
		contextMenuNode = node;
		contextMenuEdge = null;
		showContextMenu = true;
	}

	// Handle edge context menu
	function handleEdgeContextMenu(event: CustomEvent) {
		const { event: originalEvent, edge } = event.detail;
		originalEvent.preventDefault();
		contextMenuX = originalEvent.clientX;
		contextMenuY = originalEvent.clientY;
		contextMenuEdge = edge;
		contextMenuNode = null;
		showContextMenu = true;
	}

	// Close the context menu
	function closeContextMenu() {
		showContextMenu = false;
		contextMenuNode = null;
		contextMenuEdge = null;
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

		closeContextMenu();
	}

	// Delete the selected edge
	function deleteEdge() {
		if (!contextMenuEdge) return;

		edges.update((currentEdges) => currentEdges.filter((edge) => edge.id !== contextMenuEdge!.id));

		closeContextMenu();
	}

	// Context menu items - now dynamic with Phosphor icons
	const getContextMenuItems = (): ContextMenuItem[] => {
		if (contextMenuNode) {
			return [
				{
					label: 'Delete Node',
					iconComponent: Trash,
					action: deleteNode,
					danger: true
				}
			];
		} else if (contextMenuEdge) {
			return [
				{
					label: 'Delete Edge',
					iconComponent: Scissors,
					action: deleteEdge,
					danger: true
				}
			];
		}
		return [];
	};

	// Handle pane click to close context menu
	function onPaneClick() {
		if (showContextMenu) {
			closeContextMenu();
		}
	}

	// Function to handle the export button click
	function handleExport() {
		if (!socket || !isConnected) {
			console.error('Socket not connected. Cannot export.');
			exportStatus = { type: 'error', message: 'Not connected to backend.' };
			return;
		}

		// Get current nodes and edges from the stores
		let currentNodes: Node[] = [];
		let currentEdges: Edge[] = [];
		const unsubNodes = nodes.subscribe((value) => (currentNodes = value));
		const unsubEdges = edges.subscribe((value) => (currentEdges = value));
		unsubNodes();
		unsubEdges();

		const graphData = {
			nodes: currentNodes,
			edges: currentEdges
		};

		console.log('Exporting graph:', graphData);
		exportStatus = { type: 'loading', message: 'Exporting...' };
		socket.emit('export_graph', graphData);
	}
</script>

<div class="flex h-screen w-screen flex-col">
	<div class="w-full border-b border-gray-300 bg-gray-100 p-4">
		<ToolShelf onExport={handleExport} />
		<!-- Display Connection and Export Status -->
		<div class="mt-2 flex items-center justify-end space-x-2 text-xs">
			{#if !isConnected}
				<span class="rounded bg-red-100 px-1.5 py-0.5 text-red-700">Disconnected</span>
			{/if}
			{#if exportStatus.type === 'loading'}
				<span class="rounded bg-yellow-100 px-1.5 py-0.5 text-yellow-700"
					>{exportStatus.message}</span
				>
			{:else if exportStatus.type === 'success'}
				<span class="rounded bg-green-100 px-1.5 py-0.5 text-green-700">{exportStatus.message}</span
				>
			{:else if exportStatus.type === 'error'}
				<span class="rounded bg-red-100 px-1.5 py-0.5 text-red-700">{exportStatus.message}</span>
			{/if}
		</div>
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
					handleNodeContextMenu(event, node);
				}
			}}
			on:edgecontextmenu={handleEdgeContextMenu}
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
