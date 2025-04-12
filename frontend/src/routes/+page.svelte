<script lang="ts">
	import { SvelteFlow, Background, Controls, useSvelteFlow } from '@xyflow/svelte';
	import type { Node, Edge, Connection } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import ToolShelf from '$lib/components/ToolShelf.svelte';
	import TaskNode from '$lib/components/nodes/TaskNode.svelte';
	import TaskWorkerNode from '$lib/components/nodes/TaskWorkerNode.svelte';
	import LLMTaskWorkerNode from '$lib/components/nodes/LLMTaskWorkerNode.svelte';
	import JoinedTaskWorkerNode from '$lib/components/nodes/JoinedTaskWorkerNode.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import type { NodeData } from '$lib/components/nodes/TaskNode.svelte';
	import { writable, get } from 'svelte/store';
	import { allClassNames } from '$lib/stores/classNameStore';
	import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';
	import ContextMenu from '$lib/components/ContextMenu.svelte';
	import type { ContextMenuItem } from '$lib/components/ContextMenu.svelte';
	import Trash from 'phosphor-svelte/lib/Trash';
	import Scissors from 'phosphor-svelte/lib/Scissors';
	import { io, Socket } from 'socket.io-client';
	import { onMount } from 'svelte';
	import PythonInterpreterSelector from '$lib/components/PythonInterpreterSelector.svelte';
	import UploadSimple from 'phosphor-svelte/lib/UploadSimple'; // Icon for import

	// Import the Python import/export utility modules
	import {
		isPythonFile,
		readFileAsText,
		importPythonCode,
		type ImportResult,
		type BackendError
	} from '$lib/utils/pythonImport';
	import {
		exportPythonCode,
		processExportResult,
		type ExportStatus
	} from '$lib/utils/pythonExport';

	// Define node types and pass stores as props
	const nodeTypes: any = {
		task: TaskNode,
		taskworker: TaskWorkerNode,
		llmtaskworker: LLMTaskWorkerNode,
		joinedtaskworker: JoinedTaskWorkerNode
	};

	// Use SvelteFlow hook
	const { screenToFlowPosition, getNodes } = useSvelteFlow();

	// Use Svelte stores for nodes and edges
	const nodes = writable<Node[]>([]);
	const edges = writable<Edge[]>([]);

	// Socket.IO connection state
	let socket: Socket | null = null;
	let isConnected = $state(false);
	let exportStatus = $state<ExportStatus>({
		// Export status
		type: 'idle',
		message: ''
	});
	let importStatus = $state<ExportStatus>({
		// Import status
		type: 'idle',
		message: ''
	});

	// Ref for the hidden file input
	let fileInputRef: HTMLInputElement;

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
		socket.on(
			'export_result',
			(data: { success: boolean; message?: string; error?: BackendError }) => {
				// Get current nodes
				const currentNodes = get(nodes);

				// Process the export result
				const result = processExportResult(data, currentNodes);

				// Update the export status
				exportStatus = result.status;

				// If there are updated nodes (with errors), update the store
				if (result.updatedNodes) {
					nodes.set(result.updatedNodes);
				}
			}
		);

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
		let taskNameSet = new Set<string>(); // Set for task class names

		// Subscribe to get current nodes
		const unsubNodes = nodes.subscribe((currentNodes) => {
			// Reset the map and set
			nameMap = new Map();
			taskNameSet = new Set<string>();

			// Add each node's class name or worker name with its ID
			currentNodes.forEach((node) => {
				const name = node.data?.className || node.data?.workerName;
				if (name && typeof name === 'string') {
					nameMap.set(node.id, name);
				}
				// Specifically add Task node class names to the task set
				if (node.type === 'task' && node.data?.className) {
					// Cast to any first to avoid TypeScript error
					const nodeData = node.data as any as NodeData;
					taskNameSet.add(nodeData.className);
				}
			});

			// Update the stores
			allClassNames.set(nameMap);
			taskClassNamesStore.set(taskNameSet);
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

		// Get the position using screenToFlowPosition
		const position = screenToFlowPosition({
			x: event.clientX,
			y: event.clientY
		});

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
					consumeWork: `# Process the input task and produce output
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
		const newNode: Node = {
			id,
			type: nodeType,
			position,
			draggable: true,
			selectable: true,
			deletable: true,
			selected: false,
			dragging: false,
			zIndex: 0,
			data: nodeData,
			origin: [0, 0] // Set origin to top-left
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

	// --- Python Export Function ---

	// Function to handle the export button click
	function handleExport() {
		// Get current nodes and edges from the stores
		let currentNodes: Node[] = [];
		let currentEdges: Edge[] = [];
		const unsubNodes = nodes.subscribe((value) => (currentNodes = value));
		const unsubEdges = edges.subscribe((value) => (currentEdges = value));
		unsubNodes();
		unsubEdges();

		// Call the export utility function
		exportStatus = exportPythonCode(socket, currentNodes, currentEdges);
	}

	// --- Python Import Functions ---

	// Trigger the hidden file input
	function triggerImport() {
		fileInputRef?.click();
	}

	// Handle file selection
	async function handleFileSelect(event: Event) {
		const input = event.target as HTMLInputElement;
		if (!input.files || input.files.length === 0) {
			return;
		}
		const file = input.files[0];

		// Reset the input value so the same file can be selected again
		input.value = '';

		if (!isPythonFile(file)) {
			importStatus = { type: 'error', message: 'Please select a Python (.py) file.' };
			return;
		}

		importStatus = { type: 'loading', message: 'Reading file...' };

		try {
			// Read the selected file as text
			const pythonCode = await readFileAsText(file);

			// Process the file content
			await handlePythonImport(pythonCode);
		} catch (error: any) {
			importStatus = { type: 'error', message: error.message || 'Error reading file.' };
		}
	}

	// Process the Python code and update the graph
	async function handlePythonImport(pythonCode: string) {
		importStatus = { type: 'loading', message: 'Importing Python code...' };

		// Call the import utility function
		const result = await importPythonCode(pythonCode, getNodes);

		// Update the import status
		importStatus = {
			type: result.success ? 'success' : 'error',
			message: result.message
		};

		// If successful and we have new nodes, add them to the graph
		if (result.success && result.nodes && result.nodes.length > 0) {
			const newNodes = result.nodes; // Assign to variable to satisfy type system
			nodes.update((currentNodes) => [...currentNodes, ...newNodes]);
		}
	}

	// Function to check if a connection is valid
	function isValidConnection(connection: Connection | Edge): boolean {
		let currentNodes: Node[] = [];
		const unsubNodes = nodes.subscribe((value) => (currentNodes = value));
		unsubNodes();
		const targetNode = currentNodes.find((node) => node.id === connection.target);
		const sourceNode = currentNodes.find((node) => node.id === connection.source);
		if (!targetNode || !sourceNode) {
			return false;
		}
		const targetNodeData = targetNode.data as BaseWorkerData;
		if (targetNode.type !== 'mergedtaskworker' && targetNodeData.inputTypes.length > 0) {
			// all workers but merged task workers have only one input type
			return false;
		}
		return true;
	}
</script>

<div class="flex h-screen w-screen flex-col">
	<div class="w-full border-b border-gray-300 bg-gray-100 p-4">
		<ToolShelf onExport={handleExport} />

		<!-- File input (hidden) -->
		<input
			type="file"
			bind:this={fileInputRef}
			accept=".py,text/x-python"
			style="display: none;"
			onchange={handleFileSelect}
		/>

		<!-- Display Connection and Export/Import Status -->
		<div class="mt-2 flex items-center justify-end space-x-2 text-xs">
			<!-- Import Button -->
			<button
				class="flex items-center rounded bg-blue-500 px-2 py-1 text-white hover:bg-blue-600 disabled:opacity-50"
				onclick={triggerImport}
				disabled={importStatus.type === 'loading'}
				title="Import Task definitions from Python file"
			>
				<UploadSimple size={12} weight="bold" class="mr-1" />
				Import Python
			</button>

			<PythonInterpreterSelector />

			{#if !isConnected}
				<span class="rounded bg-red-100 px-1.5 py-0.5 text-red-700">Disconnected</span>
			{/if}

			<!-- Import Status Message -->
			{#if importStatus.type === 'loading'}
				<span class="rounded bg-yellow-100 px-1.5 py-0.5 text-yellow-700"
					>{importStatus.message}</span
				>
			{:else if importStatus.type === 'success'}
				<span class="rounded bg-green-100 px-1.5 py-0.5 text-green-700">{importStatus.message}</span
				>
			{:else if importStatus.type === 'error'}
				<span class="rounded bg-red-100 px-1.5 py-0.5 text-red-700">{importStatus.message}</span>
			{/if}

			<!-- Export Status Message -->
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
			{isValidConnection}
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

<style>
	:global(.svelte-flow .svelte-flow__handle) {
		width: 14px;
		height: 30px;
		border-radius: 3px;
		background-color: #784be8;
	}

	:global(.svelte-flow .svelte-flow__handle-left) {
		left: -7px;
	}

	:global(.svelte-flow .svelte-flow__handle-right) {
		right: -7px;
	}

	:global(.svelte-flow .svelte-flow__edge path, .svelte-flow__connectionline path) {
		stroke-width: 2;
	}
</style>
