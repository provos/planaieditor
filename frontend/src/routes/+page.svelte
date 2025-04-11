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

	// Type for the structured error from the backend
	interface BackendError {
		message: string;
		nodeName: string | null; // The name of the class/worker identified in the traceback
		fullTraceback?: string;
	}

	// Type for the field data coming from the import endpoint
	interface ImportedField {
		name: string;
		type: 'string' | 'integer' | 'float' | 'boolean'; // Sync with backend types
		isList: boolean;
		required: boolean;
		description?: string;
		literalValues?: string[];
	}

	// Type for the task data coming from the import endpoint
	interface ImportedTask {
		className: string;
		fields: ImportedField[];
	}

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
	let exportStatus = $state<{ type: 'idle' | 'loading' | 'success' | 'error'; message: string }>({
		// Export status
		type: 'idle',
		message: ''
	});
	let importStatus = $state<{ type: 'idle' | 'loading' | 'success' | 'error'; message: string }>({
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
				const currentNodes = get(nodes); // Get current nodes state
				clearNodeErrors(); // Clear any previous errors

				if (data.success) {
					exportStatus = { type: 'success', message: data.message || 'Export successful!' };
					console.log('Export successful:', data.message);
				} else {
					const errorInfo = data.error;
					if (!errorInfo) {
						exportStatus = { type: 'error', message: 'Unknown export error occurred.' };
						console.error('Export failed with no error details.');
						return;
					}

					console.error(`Export failed: ${errorInfo.message}`, errorInfo.fullTraceback);

					if (errorInfo.nodeName) {
						// Find the node by the name identified in the backend
						const targetNode = currentNodes.find(
							(n) =>
								n.data?.className === errorInfo.nodeName ||
								n.data?.workerName === errorInfo.nodeName
						);

						if (targetNode) {
							// Assign the core message to the specific node's data
							nodes.update((nds) =>
								nds.map((n) =>
									n.id === targetNode.id
										? { ...n, data: { ...n.data, error: errorInfo.message } }
										: n
								)
							);
							exportStatus = {
								type: 'error',
								message: `Error in node ${errorInfo.nodeName}: ${errorInfo.message}`
							};
						} else {
							// Couldn't find node for the name, show generic message with details
							console.warn(`Could not find node with name: ${errorInfo.nodeName}`);
							exportStatus = { type: 'error', message: `Error (unlinked): ${errorInfo.message}` };
						}
					} else {
						// Show generic error message if backend couldn't identify a node name
						exportStatus = { type: 'error', message: errorInfo.message };
					}
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
					const nodeData = node.data as NodeData;
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

	// --- Python Import Functions ---

	// Trigger the hidden file input
	function triggerImport() {
		fileInputRef?.click();
	}

	// Handle file selection
	function handleFileSelect(event: Event) {
		const input = event.target as HTMLInputElement;
		if (!input.files || input.files.length === 0) {
			return;
		}
		const file = input.files[0];

		if (file.type !== 'text/x-python' && !file.name.endsWith('.py')) {
			importStatus = { type: 'error', message: 'Please select a Python (.py) file.' };
			return;
		}

		const reader = new FileReader();
		reader.onload = (e) => {
			const pythonCode = e.target?.result as string;
			if (pythonCode) {
				importPythonCode(pythonCode);
			} else {
				importStatus = { type: 'error', message: 'Could not read file content.' };
			}
		};
		reader.onerror = () => {
			importStatus = { type: 'error', message: 'Error reading file.' };
		};
		reader.readAsText(file);

		// Reset the input value so the same file can be selected again
		input.value = '';
	}

	// Send code to backend and create nodes
	async function importPythonCode(pythonCode: string) {
		importStatus = { type: 'loading', message: 'Importing Python code...' };

		try {
			const response = await fetch('http://localhost:5001/api/import-python', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ python_code: pythonCode })
			});

			const result = await response.json();

			if (!response.ok || !result.success) {
				throw new Error(result.error || 'Import failed on the backend.');
			}

			const importedTasks: ImportedTask[] = result.tasks || [];

			if (importedTasks.length === 0) {
				importStatus = { type: 'success', message: 'No Task classes found in the file.' };
				return;
			}

			// Create new nodes from the imported task data
			const newNodes: Node[] = [];
			const existingNodes = getNodes(); // Get current nodes for positioning
			let nextY = existingNodes.reduce(
				(maxY, node) => Math.max(maxY, node.position.y + (node.height || 150)),
				50
			); // Start below existing nodes
			const startX = 50;

			importedTasks.forEach((task) => {
				const id = `imported-task-${task.className}-${Date.now()}`;
				const nodeData = {
					className: task.className, // Use the imported class name
					fields: task.fields.map((f) => ({
						// Map imported fields
						name: f.name,
						type: f.type, // Assuming TaskNode accepts these directly
						isList: f.isList,
						required: f.required,
						description: f.description,
						literalValues: f.literalValues
					})),
					nodeId: id // Crucial: Pass the generated node ID
				};

				const newNode: Node = {
					id,
					type: 'task', // It's a TaskNode
					position: { x: startX, y: nextY },
					draggable: true,
					selectable: true,
					deletable: true,
					selected: false,
					dragging: false,
					zIndex: 0,
					data: nodeData,
					origin: [0, 0]
				};
				newNodes.push(newNode);
				nextY += 180; // Basic vertical spacing
			});

			// Add the new nodes to the store
			nodes.update((currentNodes) => [...currentNodes, ...newNodes]);

			importStatus = {
				type: 'success',
				message: `Successfully imported ${newNodes.length} Task node(s).`
			};

			// Also update the taskClassNamesStore with the newly imported names
			const importedTaskNames = new Set(importedTasks.map((task) => task.className));
			taskClassNamesStore.update((existingNames) => {
				importedTaskNames.forEach((name) => existingNames.add(name));
				return new Set(existingNames); // Create a new set to trigger reactivity
			});
		} catch (error: any) {
			console.error('Error importing Python code:', error);
			importStatus = {
				type: 'error',
				message: `Import failed: ${error.message || 'Unknown error'}`
			};
		}
	}

	// ------------------------------

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

	// Helper function to clear errors from all node data
	function clearNodeErrors() {
		nodes.update((currentNodes) =>
			currentNodes.map((node) => {
				if (node.data?.error) {
					const { error, ...restData } = node.data; // Destructure to remove error
					return { ...node, data: restData };
				} else {
					return node; // No error property to remove
				}
			})
		);
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
