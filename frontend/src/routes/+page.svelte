<script lang="ts">
	import { nodes, edges } from '$lib/stores/graphStore';
	import { dev } from '$app/environment';
	import { backendUrl } from '$lib/utils/backendUrl';
	import { downloadFile } from '$lib/utils/utils';
	import {
		SvelteFlow,
		Background,
		Controls,
		ControlButton,
		useSvelteFlow,
		useUpdateNodeInternals
	} from '@xyflow/svelte';
	import { getEdgeStyleProps } from '$lib/utils/edgeUtils';
	import type { Node, Edge, Connection } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import ToolShelf from '$lib/components/ToolShelf.svelte';
	import ModuleLevelImport from '$lib/components/nodes/ModuleLevelImport.svelte';
	import TaskNode from '$lib/components/nodes/TaskNode.svelte';
	import TaskWorkerNode from '$lib/components/nodes/TaskWorkerNode.svelte';
	import LLMTaskWorkerNode from '$lib/components/nodes/LLMTaskWorkerNode.svelte';
	import JoinedTaskWorkerNode from '$lib/components/nodes/JoinedTaskWorkerNode.svelte';
	import TaskImportNode from '$lib/components/nodes/TaskImportNode.svelte';
	import SubGraphWorkerNode from '$lib/components/nodes/SubGraphWorkerNode.svelte';
	import ChatTaskWorkerNode from '$lib/components/nodes/ChatTaskWorkerNode.svelte';
	import DataInputNode from '$lib/components/nodes/DataInputNode.svelte';
	import DataOutputNode from '$lib/components/nodes/DataOutputNode.svelte';
	import ToolNode from '$lib/components/nodes/ToolNode.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import type { NodeData } from '$lib/components/nodes/TaskNode.svelte';
	import type { TaskImportNodeData } from '$lib/components/nodes/TaskImportNode.svelte';
	import type { DataOutputNodeData } from '$lib/components/nodes/DataOutputNode.svelte';
	import type { DataInputNodeData } from '$lib/components/nodes/DataInputNode.svelte';
	import type { ToolNodeData } from '$lib/components/nodes/ToolNode.svelte';
	import { get } from 'svelte/store';
	import { allClassNames, taskClassNamesStore, toolNamesStore } from '$lib/stores/classNameStore';
	import { socketStore } from '$lib/stores/socketStore.svelte';
	import { startLspManager, stopLspManager } from '$lib/stores/monacoStore.svelte';
	import {
		llmConfigs,
		llmConfigsFromCode,
		clearLLMConfigsFromCode,
		type LLMConfig,
		type LLMConfigFromCode
	} from '$lib/stores/llmConfigsStore';
	import ContextMenu from '$lib/components/ContextMenu.svelte';
	import type { ContextMenuItem } from '$lib/components/ContextMenu.svelte';
	import Trash from 'phosphor-svelte/lib/Trash';
	import Scissors from 'phosphor-svelte/lib/Scissors';
	import Code from 'phosphor-svelte/lib/Code';
	import ArrowsClockwise from 'phosphor-svelte/lib/ArrowsClockwise'; // Icon for layout
	import Plus from 'phosphor-svelte/lib/Plus';
	import Minus from 'phosphor-svelte/lib/Minus';
	import { io } from 'socket.io-client';
	import { onMount } from 'svelte';
	import { selectedInterpreterPath } from '$lib/stores/pythonInterpreterStore.svelte';
	import { addAvailableMethod, nodeDataFromType, addNewNode } from '$lib/utils/nodeUtils';
	import FullScreenEditor from '$lib/components/FullScreenEditor.svelte';
	import { fullScreenEditorState } from '$lib/stores/fullScreenEditorStore.svelte';
	import {
		assistantState,
		assistantResponse,
		clearAssistantMessages
	} from '$lib/stores/assistantStateStore.svelte';
	import Assistant from '$lib/components/Assistant.svelte';
	import { openSplitPane, splitPaneConfig } from '$lib/stores/splitPaneStore.svelte.ts';

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

	// Import the graphName store
	import { graphName } from '$lib/stores/graphNameStore.svelte';

	// Import the GraphNameDialog component
	import GraphNameDialog from '$lib/components/GraphNameDialog.svelte';

	// Support for Svelte Splitpanes
	import { Splitpanes, Pane } from 'svelte-splitpanes';

	// Define the structure for the saved JSON file
	interface SavedGraphState {
		version: number;
		name?: string;
		nodes: Node[];
		edges: Edge[];
		llmConfigs: LLMConfig[];
		llmConfigsFromCode: LLMConfigFromCode[];
	}

	// Define node types and pass stores as props
	const nodeTypes: any = {
		modulelevelimport: ModuleLevelImport,
		task: TaskNode,
		taskimport: TaskImportNode,
		taskworker: TaskWorkerNode,
		llmtaskworker: LLMTaskWorkerNode,
		joinedtaskworker: JoinedTaskWorkerNode,
		subgraphworker: SubGraphWorkerNode,
		chattaskworker: ChatTaskWorkerNode,
		datainput: DataInputNode,
		dataoutput: DataOutputNode,
		tool: ToolNode
	};

	// Use SvelteFlow hook
	const { screenToFlowPosition, getNodes, fitView } = useSvelteFlow();

	const updateNodeInternals = useUpdateNodeInternals();

	// Socket.IO connection state
	let exportStatus = $state<ExportStatus>({
		// Export status
		type: 'idle',
		message: ''
	});
	let loadStatus = $state<ExportStatus>({
		// Import status
		type: 'idle',
		message: ''
	});

	// State for LLM Config Modal visibility
	let showLLMConfigModal = $state(false);

	// Ref for the hidden file input for Python import
	let pythonFileInputRef: HTMLInputElement;
	// Ref for the hidden file input for JSON load
	let jsonFileInputRef: HTMLInputElement;

	// How often we tried to lay out
	let layoutAttempts: number = 0;
	let lspManagerAttempts: number = 0;

	let showGraphNameDialog = $state(false);
	let pendingActionAfterName: 'save' | 'export' | null;

	function attemptLspConnection() {
		startLspManager().then((success) => {
			if (!success) {
				lspManagerAttempts++;
				if (lspManagerAttempts < 3) {
					setTimeout(attemptLspConnection, 1000);
				} else {
					console.error('Failed to start LSP Manager');
				}
			} else {
				lspManagerAttempts = 0;
			}
		});
	}

	onMount(() => {
		if (dev) {
			// Define the convertGraphToJSON function so it can be used in the backend tests
			(window as any).convertGraphToJSON = convertGraphtoJSON;
		}

		// Connect to the Socket.IO server using the determined URL
		socketStore.socket = io(backendUrl);

		socketStore.socket.on('connect', async () => {
			console.log('Connected to backend:', socketStore.socket?.id);
			socketStore.isConnected = true;

			// Start the LSP Manager now that socket is connected
			attemptLspConnection();

			loadStatus = { type: 'idle', message: '' };
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

		socketStore.socket.on('disconnect', async () => {
			console.log('Disconnected from backend');

			// Stop the LSP Manager before marking as disconnected
			await stopLspManager();

			socketStore.isConnected = false;
			exportStatus = { type: 'idle', message: '' }; // Reset status on disconnect
		});

		socketStore.socket.on('connect_error', (err) => {
			console.error('Connection error:', err);
			socketStore.isConnected = false;
			exportStatus = { type: 'error', message: `Connection failed: ${err.message}` };
		});

		// Listen for export results from the backend
		socketStore.socket.on(
			'export_result',
			(data: {
				success: boolean;
				message?: string;
				mode?: 'export' | 'execute' | undefined;
				error?: BackendError;
				python_code?: string;
				validation_result?: any;
			}) => {
				// Get current nodes
				const currentNodes = get(nodes);

				// Process the export result
				const result = processExportResult(data, currentNodes);

				// Update the export status
				exportStatus = result.status;
				if (assistantState.isOpen) {
					// if we get a planai debug event, we will have populated the assistantResponse store
					// and set assistantState.isRunning to false. this is the fallback when something goes wrong
					if (assistantState.isRunning) {
						assistantResponse.set(
							"I did not get a response from the backend. Sorry, I'm not sure what happened."
						);
						assistantState.isRunning = false;
					}
				}

				// If there are updated nodes (with errors), update the store
				if (result.updatedNodes) {
					nodes.set(result.updatedNodes);
				}

				// If the export was successful, download the Python code
				if (data.success && data.mode === 'export' && data.python_code) {
					downloadFile(get(graphName) + '.py', data.python_code);
				}
			}
		);

		// Listen for PlanAI debug events
		socketStore.socket.on('planai_debug_event', (event: { type: string; data: any }) => {
			console.log('Received planai_debug_event:', event);

			if (event.type === 'dataoutput_callback' && event.data) {
				const { node_id, task: taskJsonString } = event.data;

				if (!node_id || !taskJsonString) {
					console.error('Missing node_id or task data in dataoutput_callback event:', event.data);
					return;
				}

				try {
					const taskData = JSON.parse(taskJsonString);

					// If assistant is open, try to pass the message to it
					if (assistantState.isOpen) {
						assistantState.isRunning = false;
						if (taskData && typeof taskData === 'object') {
							let foundResponse: string | null = null;
							for (const value of Object.values(taskData)) {
								if (typeof value === 'string') {
									foundResponse = value;
									break; // Use the first string value found
								}
							}

							if (foundResponse) {
								assistantResponse.set(foundResponse);
							} else {
								console.log(
									'No string value found in taskData to use as assistant response.',
									taskData
								);
								assistantResponse.set("I am sorry, Dave. I am afraid I can't do that.");
							}
						} else {
							console.log('TaskData is not a valid object for the assistant.', taskData);
						}
					} else {
						nodes.update((currentNodes) => {
							return currentNodes.map((node) => {
								if (node.id === node_id && node.type === 'dataoutput') {
									// Prepend the new data to the receivedData array
									const nodeData = node.data as unknown as DataOutputNodeData;
									const previousReceivedData = nodeData.receivedData || [];
									const updatedReceivedData = [taskData, ...previousReceivedData];
									return {
										...node,
										data: {
											...node.data,
											receivedData: updatedReceivedData
										}
									};
								}
								return node;
							});
						});
					}
				} catch (parseError) {
					console.error(
						'Error parsing task JSON in dataoutput_callback:',
						parseError,
						taskJsonString
					);
				}
			}
		});

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
			// Ensure the LSP Manager is stopped when component unmounts
			stopLspManager().catch((err) => {
				console.error('Error stopping LSP Manager during cleanup:', err);
			});

			// Disconnect the socket when the component is destroyed
			socketStore.socket?.emit('stop_lsp');
			socketStore.socket?.disconnect();
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
		let toolNameSet = new Set<string>(); // Set for tool names
		// Subscribe to get current nodes
		const unsubNodes = nodes.subscribe((currentNodes) => {
			// Reset the map and set
			nameMap = new Map();
			taskNameSet = new Set<string>();
			toolNameSet = new Set<string>();
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
				} else if (node.type === 'tool' && node.data?.name) {
					const nodeData = node.data as unknown as ToolNodeData;
					toolNameSet.add(nodeData.name);
				}
			});

			// Update the stores
			allClassNames.set(nameMap);
			taskClassNamesStore.set(taskNameSet);
			toolNamesStore.set(toolNameSet);
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

		// Get the position using screenToFlowPosition
		let position = screenToFlowPosition({
			x: event.clientX,
			y: event.clientY
		});

		if (nodeType === 'assistantinput') {
			// We are potentially adding two nodes
			// Check if we have a taskimport node of className "ChatTask"
			const taskImportNode = getNodes().find(
				(node) => node.type === 'taskimport' && node.data?.className === 'ChatTask'
			);
			if (!taskImportNode) {
				// We have a taskimport node, so we can add the assistantinput node
				const id = `taskimport-${Date.now()}`;
				const nodeData: TaskImportNodeData = nodeDataFromType(
					id,
					'taskimport'
				) as TaskImportNodeData;
				nodeData.modulePath = 'planai';
				nodeData.isImplicit = false;
				nodeData.availableClasses = ['ChatTask'];
				nodeData.className = 'ChatTask';
				nodeData.nodeId = id;

				addNewNode(nodes, id, 'taskimport', position, nodeData);

				position = {
					x: position.x,
					y: position.y + 200
				};
			}

			const id = `datainput-${Date.now()}`;
			const nodeData: DataInputNodeData = nodeDataFromType(id, 'datainput') as DataInputNodeData;
			nodeData.className = 'ChatTask';
			addNewNode(nodes, id, 'datainput', position, nodeData);
		} else {
			// Create a unique ID for the new node
			const id = `${nodeType}-${Date.now()}`;

			// Configure node data based on node type
			let nodeData: any = nodeDataFromType(id, nodeType);
			// Then add the node to the graph
			addNewNode(nodes, id, nodeType, position, nodeData);
		}
		if (nodeType === 'tool') {
			openSplitPane();
		}
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
			let baseNodeItems = [
				{
					label: 'Delete Node',
					iconComponent: Trash,
					action: deleteNode,
					danger: true
				}
			];

			if (
				contextMenuNode &&
				(contextMenuNode.type === 'taskworker' ||
					contextMenuNode.type === 'llmtaskworker' ||
					contextMenuNode.type === 'joinedtaskworker' ||
					contextMenuNode.type === 'subgraphworker' ||
					contextMenuNode.type === 'chattaskworker')
			) {
				const inputEdges = get(edges).filter((edge) => edge.target === contextMenuNode?.id);
				const inputNodes = inputEdges.map((edge) => edge.source);
				const hasDataInput = inputNodes.some(
					(node) => get(nodes).find((n) => n.id === node)?.type === 'datainput'
				);
				if (!hasDataInput) {
					baseNodeItems.unshift({
						label: contextMenuNode.data?.entryPoint
							? 'Remove Graph Entry Point'
							: 'Make Graph Entry Point',
						iconComponent: contextMenuNode.data?.entryPoint ? Minus : Plus,
						action: () => {
							nodes.update((currentNodes) => {
								return currentNodes.map((node) => {
									if (node.id === contextMenuNode!.id) {
										return {
											...node,
											data: {
												...node.data,
												entryPoint: !node.data?.entryPoint
											}
										};
									}
									return node;
								});
							});
							updateNodeInternals(contextMenuNode!.id);
							closeContextMenu();
						},
						danger: false
					});
				}

				if (!contextMenuNode.data?.otherMembersSource) {
					baseNodeItems.unshift({
						label: 'Add Other Members',
						iconComponent: Code,
						action: () => {
							nodes.update((currentNodes) => {
								return currentNodes.map((node) => {
									if (node.id === contextMenuNode!.id) {
										console.log('adding other members');
										return {
											...node,
											data: {
												...node.data,
												otherMembersSource: '# add member variables or custom functions here'
											}
										};
									}
									return node;
								});
							});
							closeContextMenu();
						},
						danger: false
					});
				}
			}

			// Define optional methods per worker type
			const OPTIONAL_METHODS: Record<string, string[]> = {
				llmtaskworker: ['extra_validation', 'format_prompt', 'pre_process', 'post_process']
			};

			const nodeType = contextMenuNode.type || '';
			const isCached = (contextMenuNode.data as BaseWorkerData)?.isCached || false;
			const availableOptionalMethods = OPTIONAL_METHODS[nodeType] || [];
			const existingMethods = new Set(Object.keys(contextMenuNode.data?.methods || {}));

			if (isCached) {
				availableOptionalMethods.push('extra_cache_key');
				availableOptionalMethods.push('pre_consume_work');
				availableOptionalMethods.push('post_consume_work');
			}

			const addMethodItems = availableOptionalMethods
				.filter((methodName) => !existingMethods.has(methodName))
				.map((methodName) => ({
					label: `Add ${methodName}()`,
					iconComponent: Code,
					action: () => {
						addAvailableMethod(nodes, contextMenuNode!.id, methodName);
						closeContextMenu();
					},
					danger: false
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

	function handleNodeClick(event: CustomEvent<{ event: MouseEvent; node: Node }>) {
		const { node } = event.detail;
		if (node.type === 'tool') {
			openSplitPane();
		}
	}

	// --- Clear Graph Function ---
	function handleClearGraph() {
		// Ask for confirmation before clearing
		if (confirm('Are you sure you want to clear the entire graph? This action cannot be undone.')) {
			nodes.set([]);
			edges.set([]);
			llmConfigs.set([]); // Clear user LLM configs
			llmConfigsFromCode.set([]); // Clear code LLM configs
			graphName.set('');
			clearLLMConfigsFromCode();
			clearAssistantMessages();
			console.log('Graph cleared.');
			// Optionally reset status messages
			exportStatus = { type: 'idle', message: '' };
			loadStatus = { type: 'idle', message: '' };
		}
	}

	// --- Python Export Function ---

	// Function to handle the export button click
	function handleExport(mode: 'export' | 'execute' = 'execute') {
		// Check for name only if exporting the file (not just executing)
		if (mode === 'export' && !get(graphName).trim()) {
			pendingActionAfterName = 'export';
			showGraphNameDialog = true;
			return;
		}

		// Get current nodes and edges from the stores
		let currentNodes: Node[] = [];
		let currentEdges: Edge[] = [];
		const unsubNodes = nodes.subscribe((value) => (currentNodes = value));
		const unsubEdges = edges.subscribe((value) => (currentEdges = value));
		unsubNodes();
		unsubEdges();

		// Call the export utility function
		exportStatus = exportPythonCode(socketStore.socket, currentNodes, currentEdges, mode);
	}

	// --- Python Import Functions ---

	// Trigger the hidden file input for Python import
	function triggerImport() {
		pythonFileInputRef?.click();
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
			loadStatus = { type: 'error', message: 'Please select a Python (.py) file.' };
			return;
		}

		loadStatus = { type: 'loading', message: 'Reading file...' };

		try {
			// Read the selected file as text
			const pythonCode = await readFileAsText(file);

			// Process the file content
			await handlePythonImport(pythonCode);
		} catch (error: any) {
			loadStatus = { type: 'error', message: error.message || 'Error reading file.' };
		}
	}

	// Process the Python code and update the graph
	async function handlePythonImport(pythonCode: string) {
		loadStatus = { type: 'loading', message: 'Importing Python code...' };

		// Call the import utility function
		const result = await importPythonCode(pythonCode, getNodes);

		// Update the import status
		loadStatus = {
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
		if (sourceNode.type === 'datainput') {
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

		// if the source node is a datainput, make the target node an entry point
		if (sourceNode.type == 'datainput') {
			const targetNode = get(nodes).find((node) => node.id === newEdge.target);
			if (targetNode && !(targetNode.data as BaseWorkerData).entryPoint) {
				nodes.update((nds) => {
					return nds.map((node) => {
						if (node.id === targetNode.id) {
							return { ...node, data: { ...node.data, entryPoint: true } };
						}
						return node;
					});
				});
				updateNodeInternals(targetNode.id);
			}
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

	// --- Save/Load Graph Functions ---

	// Function to handle saving the graph state to a JSON file
	function handleSave() {
		// Show dialog if unnamed
		if (!get(graphName).trim()) {
			pendingActionAfterName = 'save';
			showGraphNameDialog = true;
			return;
		}

		const currentNodes = get(nodes);
		const currentEdges = get(edges);
		const currentUserLLMConfigs = get(llmConfigs);
		const currentCodeLLMConfigs = get(llmConfigsFromCode);

		const graphState: SavedGraphState = {
			version: 1,
			name: get(graphName),
			nodes: currentNodes,
			edges: currentEdges,
			llmConfigs: currentUserLLMConfigs,
			llmConfigsFromCode: currentCodeLLMConfigs
		};

		const jsonString = JSON.stringify(graphState, null, 2);
		downloadFile(`${get(graphName) || 'planai-graph'}.json`, jsonString);

		console.log('Graph saved to JSON.');
	}

	// Handle JSON file selection for loading
	async function handleJsonFileSelect(event: Event) {
		const input = event.target as HTMLInputElement;
		if (!input.files || input.files.length === 0) {
			return;
		}
		const file = input.files[0];

		// Reset the input value
		input.value = '';

		if (file.type !== 'application/json') {
			loadStatus = { type: 'error', message: 'Please select a JSON (.json) file.' };
			return;
		}

		loadStatus = { type: 'loading', message: 'Reading JSON file...' };

		try {
			const jsonContent = await readFileAsText(file);
			await loadGraphFromJson(jsonContent);
		} catch (error: any) {
			loadStatus = { type: 'error', message: error.message || 'Error reading JSON file.' };
		}
	}

	// Process the JSON content and update the graph
	async function loadGraphFromJson(jsonContent: string) {
		loadStatus = { type: 'loading', message: 'Loading graph from JSON...' };

		try {
			const loadedState: SavedGraphState = JSON.parse(jsonContent);

			// Basic validation of the loaded structure
			if (
				!loadedState ||
				typeof loadedState !== 'object' ||
				!Array.isArray(loadedState.nodes) ||
				!Array.isArray(loadedState.edges) ||
				!Array.isArray(loadedState.llmConfigs) ||
				!Array.isArray(loadedState.llmConfigsFromCode)
			) {
				throw new Error('Invalid JSON file structure.');
			}

			// Clear existing graph FIRST
			nodes.set([]);
			edges.set([]);
			llmConfigs.set([]);
			llmConfigsFromCode.set([]);
			clearAssistantMessages();
			// Introduce a small delay before setting new data to ensure reactivity
			await new Promise((resolve) => setTimeout(resolve, 10));

			// Load data from the file
			nodes.set(loadedState.nodes);
			edges.set(loadedState.edges);
			llmConfigs.set(loadedState.llmConfigs);
			llmConfigsFromCode.set(loadedState.llmConfigsFromCode);

			// Restore graph name if it exists in the loaded state
			if (loadedState.name) {
				graphName.set(loadedState.name);
			}

			loadStatus = { type: 'success', message: 'Graph loaded successfully.' };

			// Recompute all edge styles
			edges.update((eds) => {
				return eds.map((edge) => {
					const sourceNode = get(nodes).find((node) => node.id === edge.source);
					if (!sourceNode) {
						console.error('sourceNode not found');
						return edge;
					}
					return { ...edge, style: getEdgeStyleProps(sourceNode, edge).style };
				});
			});

			// Use setTimeout to allow Svelte to render nodes first before layout
			setTimeout(runElkLayout, 100);
		} catch (error: any) {
			console.error('Error loading graph from JSON:', error);
			loadStatus = {
				type: 'error',
				message: `Load failed: ${error.message || 'Invalid JSON format'}`
			};
			// Optionally clear again on error to prevent partial loading state
			nodes.set([]);
			edges.set([]);
			llmConfigs.set([]);
			llmConfigsFromCode.set([]);
			clearAssistantMessages();
			graphName.set(''); // Reset graph name on error
		}
	}

	// Trigger the hidden JSON file input
	function triggerLoad() {
		jsonFileInputRef?.click();
	}

	let currentGraphName = $state(get(graphName));
	graphName.subscribe((value) => {
		currentGraphName = value;
	});
</script>

{#if fullScreenEditorState.isOpen}
	<FullScreenEditor />
{/if}

{#if assistantState.isOpen}
	<Assistant />
{/if}

<div class="flex h-screen w-screen flex-col">
	<div class="w-full border-b border-gray-300 bg-gray-100 p-4">
		<ToolShelf
			onExport={() => handleExport('export')}
			onExecute={() => handleExport('execute')}
			onClearGraph={handleClearGraph}
			onImport={triggerImport}
			onSave={handleSave}
			onLoad={triggerLoad}
			onConfigureLLMs={() => (showLLMConfigModal = true)}
			onLoadJSON={loadGraphFromJson}
			graphName={currentGraphName}
			onGraphNameChange={(name) => graphName.set(name)}
		/>

		<!-- Hidden File input for Python import -->
		<input
			type="file"
			bind:this={pythonFileInputRef}
			accept=".py,text/x-python"
			style="display: none;"
			onchange={handleFileSelect}
			data-testid="file-input"
		/>
		<!-- Hidden File input for JSON load -->
		<input
			type="file"
			bind:this={jsonFileInputRef}
			accept=".json,application/json"
			style="display: none;"
			onchange={handleJsonFileSelect}
			data-testid="json-file-input"
		/>

		<!-- Display Connection and Export/Import Status -->
		<div class="mt-2 flex items-center justify-end space-x-2 text-xs">
			{#if !socketStore.isConnected}
				<span class="rounded bg-red-100 px-1.5 py-0.5 text-red-700">Disconnected</span>
			{/if}

			<!-- Load Status Message -->
			{#if loadStatus.type === 'loading'}
				<span class="rounded bg-yellow-100 px-1.5 py-0.5 text-yellow-700">{loadStatus.message}</span
				>
			{:else if loadStatus.type === 'success'}
				<span class="rounded bg-green-100 px-1.5 py-0.5 text-green-700">{loadStatus.message}</span>
			{:else if loadStatus.type === 'error'}
				<span class="rounded bg-red-100 px-1.5 py-0.5 text-red-700">{loadStatus.message}</span>
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
		<Splitpanes horizontal={false}>
			<Pane maxSize={100} size={100}>
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
					on:nodeclick={handleNodeClick}
				>
					<Background />
					<Controls>
						<ControlButton onclick={runElkLayout} title="Re-run Layout">
							<ArrowsClockwise size={16} />
						</ControlButton>
					</Controls>
				</SvelteFlow>
			</Pane>
			<Pane maxSize={25} size={splitPaneConfig.isOpen ? 25 : 0} snapSize={5}>
				<Splitpanes horizontal={true}>
					<Pane>Config Pane</Pane>
					<Pane minSize={25} maxSize={75}>List Pane</Pane>
				</Splitpanes>
			</Pane>
		</Splitpanes>

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

		{#if showGraphNameDialog}
			<GraphNameDialog
				open={showGraphNameDialog}
				onClose={() => {
					showGraphNameDialog = false;
					pendingActionAfterName = null; // Clear action on cancel
				}}
				initialName={get(graphName)}
				onSave={(name) => {
					graphName.set(name);
					showGraphNameDialog = false; // Close dialog first
					const action = pendingActionAfterName;
					pendingActionAfterName = null; // Clear action
					// Trigger the pending action
					if (action === 'save') {
						handleSave();
					} else if (action === 'export') {
						handleExport('export');
					}
				}}
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
