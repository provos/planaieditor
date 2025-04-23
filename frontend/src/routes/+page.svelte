<script lang="ts">
	import { dev } from '$app/environment';
	import { persisted } from 'svelte-persisted-store';
	import { backendUrl } from '$lib/utils/backendUrl';

	import { SvelteFlow, Background, Controls, ControlButton, useSvelteFlow } from '@xyflow/svelte';
	import { getEdgeStyleProps } from '$lib/utils/edgeUtils';
	import type { Node, Edge, Connection } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import ToolShelf from '$lib/components/ToolShelf.svelte';
	import TaskNode from '$lib/components/nodes/TaskNode.svelte';
	import TaskWorkerNode from '$lib/components/nodes/TaskWorkerNode.svelte';
	import LLMTaskWorkerNode from '$lib/components/nodes/LLMTaskWorkerNode.svelte';
	import JoinedTaskWorkerNode from '$lib/components/nodes/JoinedTaskWorkerNode.svelte';
	import TaskImportNode from '$lib/components/nodes/TaskImportNode.svelte';
	import SubGraphWorkerNode from '$lib/components/nodes/SubGraphWorkerNode.svelte';
	import ChatTaskWorkerNode from '$lib/components/nodes/ChatTaskWorkerNode.svelte';
	import DataInputNode from '$lib/components/nodes/DataInputNode.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import type { NodeData } from '$lib/components/nodes/TaskNode.svelte';
	import { get } from 'svelte/store';
	import { allClassNames } from '$lib/stores/classNameStore';
	import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';
	import { clearLLMConfigsFromCode } from '$lib/stores/llmConfigsStore';
	import ContextMenu from '$lib/components/ContextMenu.svelte';
	import type { ContextMenuItem } from '$lib/components/ContextMenu.svelte';
	import Trash from 'phosphor-svelte/lib/Trash';
	import Scissors from 'phosphor-svelte/lib/Scissors';
	import { io, Socket } from 'socket.io-client';
	import { onMount } from 'svelte';
	import { selectedInterpreterPath } from '$lib/stores/pythonInterpreterStore.svelte';
	import Code from 'phosphor-svelte/lib/Code';
	import ArrowsClockwise from 'phosphor-svelte/lib/ArrowsClockwise'; // Icon for layout

	// Import utility for default method bodies
	import { getDefaultMethodBody } from '$lib/utils/defaults';

	// Import the LLM Config Modal
	import LLMConfigModal from '$lib/components/LLMConfigModal.svelte';

	// Import the Python import/export utility modules
	import {
		isPythonFile,
		readFileAsText,
		importPythonCode,
		type BackendError
	} from '$lib/utils/pythonImport';
	import {
		exportPythonCode,
		processExportResult,
		type ExportStatus,
		convertGraphtoJSON
	} from '$lib/utils/pythonExport';

	// Import the ELKjs layout function
	import { layoutGraph } from '$lib/utils/pythonImport';

	// Define node types and pass stores as props
	const nodeTypes: any = {
		task: TaskNode,
		taskimport: TaskImportNode,
		taskworker: TaskWorkerNode,
		cachedtaskworker: TaskWorkerNode,
		llmtaskworker: LLMTaskWorkerNode,
		cachedllmtaskworker: LLMTaskWorkerNode,
		joinedtaskworker: JoinedTaskWorkerNode,
		subgraphworker: SubGraphWorkerNode,
		chattaskworker: ChatTaskWorkerNode,
		datainput: DataInputNode
	};

	// Use SvelteFlow hook
	const { screenToFlowPosition, getNodes, fitView } = useSvelteFlow();

	// Use persisted Svelte stores for nodes and edges
	const nodes = persisted<Node[]>('nodes', []);
	const edges = persisted<Edge[]>('edges', []);

	// Socket.IO connection state
	let socket: Socket | null = $state(null);
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

	// State for LLM Config Modal visibility
	let showLLMConfigModal = $state(false);

	// Ref for the hidden file input
	let fileInputRef: HTMLInputElement;

	// How often we tried to lay out
	let layoutAttempts: number = 0;

	onMount(() => {
		if (dev) {
			// Define the convertGraphToJSON function so it can be used in the backend tests
			(window as any).convertGraphToJSON = convertGraphtoJSON;
		}

		// Connect to the Socket.IO server using the determined URL
		socket = io(backendUrl);

		socket.on('connect', async () => {
			console.log('Connected to backend:', socket?.id);
			isConnected = true;

			importStatus = { type: 'idle', message: '' };
			exportStatus = { type: 'idle', message: '' };

			// Re-set interpreter on reconnect if one was selected
			const currentPath = selectedInterpreterPath.value;
			if (currentPath) {
				console.log('Re-setting interpreter on backend reconnect:', currentPath);
				try {
					// Use the dynamic backendUrl for the API call
					const response = await fetch(`${backendUrl}/api/set-venv`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json'
						},
						body: JSON.stringify({ path: currentPath })
					});
					const data = await response.json();
					if (!data.success) {
						console.error('Failed to re-set interpreter:', data.error);
						// Optionally clear the store value or show an error
						// selectedInterpreterPath.value = null;
					}
				} catch (err) {
					console.error('Error re-setting interpreter:', err);
					// Optionally clear the store value or show an error
					// selectedInterpreterPath.value = null;
				}
			}
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

		// ensure consistent edge styling after reload
		edges.update((currentEdges: Edge[]) => {
			return currentEdges.map((svelteEdge) => {
				const sourceNode = getNodes().find((n) => n.id === svelteEdge.source);
				// Use the new utility function
				const styleProps = getEdgeStyleProps(sourceNode, svelteEdge);

				return {
					...svelteEdge,
					style: styleProps.style,
					animated: styleProps.animated
				};
			});
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
		layoutAttempts = 0;

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
				if ((node.type === 'task' || node.type === 'taskimport') && node.data?.className) {
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
			case 'taskimport': {
				nodeData = {
					modulePath: '', // Initial empty module path
					className: null,
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
					output_types: [],
					methods: {
						consume_work: `# Process the input task and produce output\n# self.publish_work(output_task, input_task=task)\npass`
					},
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
					output_types: [],
					prompt: `# Process the task using an LLM
Analyze the following information and provide a response.`,
					system_prompt: `You are a helpful task processing assistant.`,
					extraValidation: 'return None',
					formatPrompt: 'return self.prompt',
					preProcess: 'return task',
					postProcess: 'return task',
					enabledFunctions: {
						extraValidation: false,
						formatPrompt: false,
						preProcess: false,
						postProcess: false
					},
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
					output_types: [],
					joinMethod: 'merge',
					nodeId: id
				};
				break;
			}
			case 'subgraphworker': {
				const baseName = 'SubGraphWorker';
				const uniqueName = generateUniqueName(baseName, existingNames);
				nodeData = {
					workerName: uniqueName, // Assign the unique name
					inputTypes: [],
					output_types: [],
					nodeId: id
				};
				break;
			}
			case 'chattaskworker': {
				const baseName = 'ChatTaskWorker';
				const uniqueName = generateUniqueName(baseName, existingNames);
				nodeData = {
					workerName: uniqueName, // Assign the unique name
					inputTypes: ['ChatTask'],
					output_types: ['ChatMessage'],
					nodeId: id
				};
				break;
			}
			case 'datainput': {
				// No name generation needed for data input
				nodeData = {
					className: null, // Start with no Task type selected
					jsonData: '{}', // Default to empty JSON
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
			const baseNodeItems = [
				{
					label: 'Delete Node',
					iconComponent: Trash,
					action: deleteNode,
					danger: true
				}
			];

			// Define optional methods per worker type
			const OPTIONAL_METHODS: Record<string, string[]> = {
				taskworker: ['pre_consume_work', 'post_consume_work'],
				cachedtaskworker: ['pre_consume_work', 'post_consume_work', 'extra_cache_key'],
				llmtaskworker: [
					'pre_consume_work',
					'post_consume_work',
					'extra_validation',
					'format_prompt',
					'pre_process',
					'post_process'
				],
				cachedllmtaskworker: [
					'pre_consume_work',
					'post_consume_work',
					'extra_validation',
					'format_prompt',
					'pre_process',
					'post_process',
					'extra_cache_key'
				]
				// Add other worker types if they have optional methods
			};

			const nodeType = contextMenuNode.type || '';
			const availableOptionalMethods = OPTIONAL_METHODS[nodeType] || [];
			const existingMethods = new Set(Object.keys(contextMenuNode.data?.methods || {}));

			const addMethodItems = availableOptionalMethods
				.filter((methodName) => !existingMethods.has(methodName))
				.map((methodName) => ({
					label: `Add ${methodName}()`,
					iconComponent: Code,
					action: () => {
						nodes.update((currentNodes) => {
							return currentNodes.map((node) => {
								if (node.id === contextMenuNode!.id) {
									const updatedMethods = {
										...(node.data.methods || {}),
										[methodName]: getDefaultMethodBody(methodName)
									};
									return {
										...node,
										data: {
											...node.data,
											methods: updatedMethods
										}
									};
								}
								return node;
							});
						});
						closeContextMenu();
					}
				}));

			return [...addMethodItems, ...baseNodeItems]; // Combine add method items and base items
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

	// --- Clear Graph Function ---
	function handleClearGraph() {
		// Ask for confirmation before clearing
		if (confirm('Are you sure you want to clear the entire graph? This action cannot be undone.')) {
			nodes.set([]);
			edges.set([]);
			clearLLMConfigsFromCode();
			console.log('Graph cleared.');
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

		// If successful and we have new nodes/edges, add them to the graph
		if (result.success) {
			if (result.nodes && result.nodes.length > 0) {
				const newNodes = result.nodes;
				nodes.update((currentNodes) => [...currentNodes, ...newNodes]);
			}
			if (result.edges && result.edges.length > 0) {
				const newEdges = result.edges;
				edges.update((currentEdges) => [...currentEdges, ...newEdges]);
			}

			// Schedule layout *after* nodes/edges are added and rendered
			if (result.success && (result.nodes?.length || result.edges?.length)) {
				// Use setTimeout to allow Svelte to render nodes first
				setTimeout(runElkLayout, 100);
			}
		}
	}

	// Function to run ELK layout
	async function runElkLayout() {
		console.log('Running ELK layout...');
		const currentNodes = get(nodes);
		const currentEdges = get(edges);

		// Basic check: Ensure nodes have dimensions before layout
		const allNodesHaveDimensions = currentNodes.every(
			(node) =>
				node.measured?.width &&
				node.measured.width > 0 &&
				node.measured?.height &&
				node.measured.height > 0
		);

		if (!allNodesHaveDimensions && layoutAttempts < 10) {
			console.warn('Node dimensions not available yet, retrying layout shortly...');
			setTimeout(runElkLayout, 200 + layoutAttempts * 100); // Increased retry delay
			layoutAttempts++;
			return;
		}
		layoutAttempts = 0;

		try {
			const { nodes: layoutedNodes, edges: layoutedEdges } = await layoutGraph(
				currentNodes,
				currentEdges
			);

			// Update positions of existing nodes instead of replacing the array
			nodes.update((nds) => {
				const nodeMap = new Map(layoutedNodes.map((n) => [n.id, n]));
				return nds.map((node) => {
					const layoutedNode = nodeMap.get(node.id);
					if (layoutedNode && layoutedNode.position) {
						// Create a new object with updated position to trigger reactivity
						return { ...node, position: layoutedNode.position };
					}
					return node; // Return original node if not found in layout results
				});
			});

			// Still set edges directly, as edge paths might change
			edges.set(layoutedEdges);

			// Use requestAnimationFrame to fitView after the DOM updates
			requestAnimationFrame(() => {
				fitView({ padding: 0.1 }); // Add padding
			});
			console.log('ELK layout applied.');
		} catch (error) {
			console.error('Error during ELK layout:', error);
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
		// Get source className based on node type
		let sourceClassName = null;
		if (sourceNode.type === 'task' || sourceNode.type === 'datainput' || sourceNode.type === 'taskimport') {
			sourceClassName = (sourceNode.data as unknown as NodeData).className;
		} else if (connection.sourceHandle) {
			sourceClassName = connection.sourceHandle.split('-')[1];
		}

		if (
			targetNode.type !== 'mergedtaskworker' &&
			targetNodeData.inputTypes.length > 0 &&
			(!sourceClassName || !targetNodeData.inputTypes.includes(sourceClassName))
		) {
			// all workers but merged task workers have only one input type
			return false;
		}
		return true;
	}

	function handleConnect(connection: Connection) {
		// find the newly created edge
		const newEdge = get(edges).find(
			(edge) => edge.source === connection.source && edge.target === connection.target
		);
		if (!newEdge) {
			console.error('newEdge not found');
			return;
		}
		const sourceNode = get(nodes).find((node) => node.id === newEdge.source);
		if (!sourceNode) {
			console.error('sourceNode not found');
			return;
		}

		// Use the utility function to get edge style properties
		const styleProps = getEdgeStyleProps(sourceNode, newEdge);
		newEdge.style = styleProps.style;
		newEdge.animated = styleProps.animated;

		edges.update((eds) => {
			const index = eds.findIndex((edge) => edge.id === newEdge.id);
			if (index !== -1) {
				eds[index] = newEdge;
			}
			return eds;
		});
	}
</script>

<div class="flex h-screen w-screen flex-col">
	<div class="w-full border-b border-gray-300 bg-gray-100 p-4">
		<ToolShelf
			onExport={handleExport}
			onClearGraph={handleClearGraph}
			onImport={triggerImport}
			onConfigureLLMs={() => (showLLMConfigModal = true)}
		/>

		<!-- File input (hidden) -->
		<input
			type="file"
			bind:this={fileInputRef}
			accept=".py,text/x-python"
			style="display: none;"
			onchange={handleFileSelect}
			data-testid="file-input"
		/>

		<!-- Display Connection and Export/Import Status -->
		<div class="mt-2 flex items-center justify-end space-x-2 text-xs">
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
			minZoom={0.05}
			ondrop={onDrop}
			ondragover={onDragOver}
			onclick={onPaneClick}
			onconnect={handleConnect}
			{isValidConnection}
			defaultEdgeOptions={{ type: 'smoothstep', style: 'stroke-width: 3;' }}
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
			<Controls>
				<ControlButton on:click={runElkLayout} title="Re-run Layout">
					<ArrowsClockwise size={16} />
				</ControlButton>
			</Controls>
		</SvelteFlow>

		{#if showContextMenu}
			<ContextMenu
				items={getContextMenuItems()}
				x={contextMenuX}
				y={contextMenuY}
				onClose={closeContextMenu}
			/>
		{/if}

		{#if showLLMConfigModal}
			<LLMConfigModal bind:showModal={showLLMConfigModal} />
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

	/* Restore appropriate cursors for interactive elements */
	:global(.svelte-flow .svelte-flow__node input) {
		cursor: text;
	}

	:global(.svelte-flow .svelte-flow__node button) {
		cursor: pointer;
	}

	:global(.svelte-flow .svelte-flow__node select) {
		cursor: pointer;
	}

	/* Ensure code editor sections have text cursor */
	:global(.svelte-flow .svelte-flow__node .cm-editor) {
		cursor: text;
	}

	:global(.svelte-flow .svelte-flow__node .cm-content) {
		cursor: text;
	}
</style>
