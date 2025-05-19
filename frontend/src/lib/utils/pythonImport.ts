import { backendUrl } from '$lib/utils/backendUrl';
import type { Node, Edge } from '@xyflow/svelte';
import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';
import { allClassNames } from '$lib/stores/classNameStore';
import { get } from 'svelte/store';
import ELK from 'elkjs/lib/elk.bundled.js';
import { Position } from '@xyflow/svelte';
import { getEdgeStyleProps } from '$lib/utils/edgeUtils';
import { addLLMConfigFromCode } from '$lib/stores/llmConfigsStore';

// Type for the structured error from the backend
export interface BackendError {
	message: string;
	nodeName: string | null; // The name of the class/worker identified in the traceback
	fullTraceback?: string;
}

// Type for the field data coming from the import endpoint
export interface ImportedField {
	name: string;
	type: string; // Can be primitive types or custom Task names
	isList: boolean;
	required: boolean;
	description?: string;
	literalValues?: string[];
}

// Type for the task data coming from the import endpoint
export interface ImportedTask {
	className: string;
	fields: ImportedField[];
}

// --- New Interfaces for Workers ---
export interface ImportedClassVar {
	name: string;
	value: any; // Can be string, number, boolean, list of strings, or a special Field object
	isField?: boolean;
	type?: string; // Type from annotation if Field()
	description?: string; // Description if Field()
}

export interface ImportedMethod {
	name: string;
	source: string; // The unparsed source code of the method
}

export interface ImportedOtherMember {
	name: string;
	source: string; // Unparsed source of assignments or unknown methods
}

export interface ImportedWorker {
	className?: string;
	workerType: string; // e.g., "taskworker", "llmtaskworker", "subgraphworker"
	classVars?: Record<string, any>; // Dictionary of known parsed class vars
	inputTypes?: string[]; // Optional: Parsed from consume_work type hint
	methods?: Record<string, string>; // Dictionary of known method sources
	otherMembersSource?: string; // Consolidated source code of other members
	variableName?: string; // Optional: Variable name assigned
	factoryFunction?: string; // Name of the factory function if applicable
	factoryInvocation?: string; // Combined invocation string
	llmConfigFromCode?: Record<string, any>; // LLM configuration parsed from code
	llmConfigVar?: string; // Variable name assigned to the LLM config if applicable
	code?: string; // Code for the module level import
	isCached: boolean;
	entryPoint?: boolean;
}

// Result type for the Python import operation
export interface ImportResult {
	success: boolean;
	message: string;
	nodes?: Node[];
	edges?: Edge[];
}

// --- Type for Edges from Backend --- //
export interface ImportedEdge {
	source: string; // Class name of source worker
	target: string; // Class name of target worker
	targetInputType?: string; // Optional: Input type name of the target worker
}

// Interface for the new imported task references from backend
export interface ImportedTaskReference {
	modulePath: string;
	className: string;
	isImplicit?: boolean;
}

// --- Type for Edges from Backend --- //
export interface ImportedEdge {
	source: string; // Class name of source worker
	target: string; // Class name of target worker
	targetInputType?: string; // Optional: Input type name of the target worker
	message: string;
	nodes?: Node[];
	edges?: Edge[];
	importedTasks?: ImportedTaskReference[]; // Add the new field
}

// --- ELKjs Layout Function --- //
const elk = new ELK();

// Default ELK options
const elkOptions = {
	'elk.algorithm': 'layered',
	'elk.layered.spacing.nodeNodeBetweenLayers': '120',
	'elk.spacing.nodeNode': '100',
	'elk.layered.cycleBreaking.strategy': 'GREEDY',
	'elk.edgeRouting': 'SPLINES',
	'elk.direction': 'RIGHT'
};

// Minimal fallback dimensions if node size isn't available yet
const MIN_NODE_WIDTH = 150;
const MIN_NODE_HEIGHT = 50;

export async function layoutGraph(
	nodesToLayout: Node[],
	edgesToLayout: Edge[],
	options = elkOptions
): Promise<{ nodes: Node[]; edges: Edge[] }> {
	const graph = {
		id: 'root',
		layoutOptions: options,
		children: nodesToLayout.map((node) => ({
			...node,
			targetPosition: Position.Top,
			sourcePosition: Position.Bottom,
			width: node.measured?.width && node.measured.width > 0 ? node.measured.width : MIN_NODE_WIDTH,
			height:
				node.measured?.height && node.measured.height > 0 ? node.measured.height : MIN_NODE_HEIGHT
		})),
		// Map Svelte Flow edges to ELK edges
		edges: edgesToLayout.map((edge) => ({
			...edge,
			id: edge.id,
			sources: [edge.source],
			targets: [edge.target]
		}))
	};

	try {
		const layoutedGraph = await elk.layout(graph);
		return {
			nodes:
				layoutedGraph.children?.map((node) => ({
					...node,
					// Copy original data back
					data: nodesToLayout.find((n) => n.id === node.id)?.data || {},
					// ELK returns x, y; Svelte Flow expects position {x, y}
					position: { x: node.x ?? 0, y: node.y ?? 0 }
				})) ?? [], // Handle cases where children might be undefined

			// Map ELK edges back to Svelte Flow edges
			edges:
				layoutedGraph.edges?.map((edge) => ({
					...edge,
					id: edge.id,
					source: edge.sources[0],
					target: edge.targets[0]
				})) ?? []
		};
	} catch (error) {
		console.error('ELK layout failed:', error);
		// Return original nodes/edges if layout fails
		return { nodes: nodesToLayout, edges: edgesToLayout };
	}
}

/**
 * Validates a file is a Python file based on type and extension
 */
export function isPythonFile(file: File): boolean {
	return file.type === 'text/x-python' || file.name.endsWith('.py');
}

/**
 * Reads a file as text using FileReader
 */
export function readFileAsText(file: File): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = (e) => {
			const content = e.target?.result as string;
			if (content) {
				resolve(content);
			} else {
				reject(new Error('Could not read file content.'));
			}
		};
		reader.onerror = () => reject(new Error('Error reading file.'));
		reader.readAsText(file);
	});
}

/**
 * Imports Python code by sending it to the backend and creating node objects from the response
 * @param pythonCode Python code to import
 * @param getNodes Function to get current nodes (for positioning)
 * @returns Promise with import result containing success/error status and new nodes if successful
 */
export async function importPythonCode(
	pythonCode: string,
	getNodes: () => Node[]
): Promise<ImportResult> {
	try {
		const response = await fetch(`${backendUrl}/api/import-python`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ python_code: pythonCode })
		});

		// Check if the response is JSON
		const contentType = response.headers.get('content-type');
		if (!contentType || !contentType.includes('application/json')) {
			const textError = await response.text();
			throw new Error(
				`Unexpected response format: ${response.status} ${response.statusText}. Response: ${textError}`
			);
		}

		const result = await response.json();

		if (!response.ok || !result.success) {
			const errorMsg = result.error
				? typeof result.error === 'string'
					? result.error
					: JSON.stringify(result.error)
				: 'Import failed on the backend with no specific error message.';
			throw new Error(errorMsg);
		}

		const importedTasks: ImportedTask[] = result.tasks || [];
		const importedWorkers: ImportedWorker[] = result.workers || [];
		const importedEdges: ImportedEdge[] = result.edges || [];
		const importedTaskReferences: ImportedTaskReference[] = result.imported_tasks || []; // Get imported task references

		if (
			importedTasks.length === 0 &&
			importedWorkers.length === 0 &&
			importedTaskReferences.length === 0
		) {
			return {
				success: true,
				message: 'No Task or Worker classes found.'
			};
		}

		// --- Create Task Nodes ---
		const newNodes: Node[] = [];
		const existingNodes = getNodes(); // Get current nodes for positioning
		let nextY = existingNodes.reduce(
			(maxY, node) => Math.max(maxY, node.position.y + (node.height || 150)),
			50
		); // Start below existing nodes
		const startX = 50;
		const classNameToNodeId: Record<string, string> = {}; // Map className to generated Node ID

		importedTasks.forEach((task) => {
			const id = `imported-task-${task.className}-${Date.now()}`;
			classNameToNodeId[task.className] = id; // Store mapping
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

		// --- Create Task Import Nodes --- //
		importedTaskReferences.forEach((importedTaskRef) => {
			const id = `imported-taskref-${importedTaskRef.className}-${Date.now()}`;
			classNameToNodeId[importedTaskRef.className] = id; // Store mapping

			const nodeData = {
				modulePath: importedTaskRef.modulePath,
				className: importedTaskRef.className, // Store class name
				isImplicit: importedTaskRef.isImplicit,
				fields: [], // Fields will be fetched by the node itself
				nodeId: id // Crucial: Pass the generated node ID
			};

			const newNode: Node = {
				id,
				type: 'taskimport', // Use the new node type
				position: { x: startX, y: nextY }, // Position with other tasks for now
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

		// --- Create Worker Nodes ---
		nextY = 0;

		// Get existing names to avoid conflicts
		const existingNames = new Set(Object.values(get(allClassNames)));

		importedWorkers.forEach((worker) => {
			// Basic check for name collision (though backend should ideally handle this)
			if (existingNames.has(worker.className)) {
				console.warn(
					`Worker class name "${worker.className}" already exists. Skipping import for this worker.`
				);
				return; // Skip this worker
			}

			const id = `imported-${worker.workerType}-${worker.className}-${Date.now()}`;
			if (worker.className) {
				classNameToNodeId[worker.className] = id; // Store mapping
			}

			// Map backend data to frontend node data structure
			const nodeData: any = convertWorkerToNodeData(worker, id);

			const newNode: Node = {
				id,
				type: worker.workerType, // Use the identified worker type
				position: { x: startX + 400, y: nextY }, // Offset workers horizontally
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
			nextY += 180; // Basic vertical spacing (adjust as needed)
		});

		// --- Create Module Level Import Node --- //
		if (result.module_imports) {
			const nodeData = {
				code: result.module_imports
			};
			const moduleLevelImportNode: Node = {
				id: `imported-module-level-${Date.now()}`,
				type: 'modulelevelimport',
				position: { x: startX + 400, y: nextY },
				draggable: true,
				selectable: true,
				deletable: true,
				selected: false,
				dragging: false,
				zIndex: 0,
				data: nodeData,
				origin: [0, 0]
			};
			newNodes.push(moduleLevelImportNode);
			nextY += 180; // Basic vertical spacing (adjust as needed)
		}

		// --- Create Edges --- //
		const newEdges: Edge[] = [];
		importedEdges.forEach((edge) => {
			const sourceNodeId = classNameToNodeId[edge.source];
			const targetNodeId = classNameToNodeId[edge.target];

			if (sourceNodeId && targetNodeId) {
				const edgeId = `imported-edge-${sourceNodeId}-${targetNodeId}`;
				const svelteEdge: Edge = {
					id: edgeId,
					source: sourceNodeId,
					target: targetNodeId
				};
				// If the target has a specific input type, connect to the corresponding source handle
				if (edge.targetInputType) {
					svelteEdge.sourceHandle = `output-${edge.targetInputType}`;
				}
				// If targetInputType is not specified, sourceHandle remains undefined,
				// connecting to the default source handle (if one exists).
				newEdges.push(svelteEdge);
			} else {
				console.warn(
					`Could not create edge for ${edge.source} -> ${edge.target}: Node ID not found.`
				);
			}
		});

		// --- Apply Edge Styling based on Source Task Type ---
		const styledEdges = newEdges.map((svelteEdge) => {
			const sourceNode = newNodes.find((n) => n.id === svelteEdge.source);
			// Use the new utility function
			const styleProps = getEdgeStyleProps(sourceNode, svelteEdge);

			return {
				...svelteEdge,
				style: styleProps.style,
				animated: styleProps.animated
			};
		});

		// Update the taskClassNamesStore with the newly imported names
		const importedTaskNames = new Set(importedTasks.map((task) => task.className));
		taskClassNamesStore.update((existingNames) => {
			importedTaskNames.forEach((name) => existingNames.add(name));
			return new Set(existingNames); // Create a new set to trigger reactivity
		});

		// --- Create Tool Nodes --- //
		const importedToolsDefinition: { name: string; description: string | null; code: string }[] =
			result.tools || [];
		importedToolsDefinition.forEach((toolDef) => {
			const id = `imported-tool-${toolDef.name.replace(/\s+/g, '_')}-${Date.now()}`;
			// classNameToNodeId[toolDef.name] = id; // Tools don't typically connect via edges by name like workers/tasks

			const nodeData = {
				name: toolDef.name,
				description: toolDef.description,
				code: toolDef.code,
				nodeId: id
			};

			const newNode: Node = {
				id,
				type: 'tool',
				position: { x: startX + 800, y: nextY }, // Position tools further to the right
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
			nextY += 280; // Adjust vertical spacing for tool nodes (they can be taller)
		});

		return {
			success: true,
			message: `Imported ${importedTasks.length} Task(s), ${importedTaskReferences.length} TaskImport(s), ${importedWorkers.length} Worker(s), and ${importedToolsDefinition.length} Tool(s).`,
			nodes: newNodes, // Return original nodes (without layout positions yet)
			edges: styledEdges // Return styled edges
		};
	} catch (error: any) {
		console.error('Error importing Python code:', error);
		return {
			success: false,
			message: `Import failed: ${error.message || 'Unknown error'}`
		};
	}
}

export function convertWorkerToNodeData(worker: ImportedWorker, id: string) {
	const nodeData: any = {
		isCached: worker.isCached || false,
		entryPoint: worker.entryPoint || false,
		variableName: worker.variableName, // Use variableName if it exists
		workerName: worker.className, // Use className as workerName
		nodeId: id,
		// Initialize common fields, specific nodes might override
		inputTypes: worker.inputTypes || [], // Use parsed inputTypes from backend if available
		output_types: worker.classVars?.output_types || [], // Map output_types

		// Store unparsed methods and members for potential display/editing later
		methods: worker.methods || {}, // Ensure methods exists
		otherMembersSource: worker.otherMembersSource || undefined, // Store consolidated source
		classVars: worker.classVars || {} // Store the rest of class vars for now
	};

	// Store the llmConfigFromCode if present for display in the UI
	if (worker.llmConfigFromCode) {
		nodeData.llmConfigFromCode = worker.llmConfigFromCode;
		nodeData.llmConfigVar = worker.llmConfigVar;

		// Add a human-readable description of the imported LLM config
		const provider = worker.llmConfigFromCode.provider.value || 'unknown';
		const modelName = worker.llmConfigFromCode.model_name.value || 'unknown';
		nodeData.llmConfigDescription = `Imported: ${provider} / ${modelName}`;

		// Log the imported LLM config for debugging
		console.log(`Imported LLM config for ${worker.className}:`, worker.llmConfigFromCode);

		if (worker.llmConfigVar) {
			// Add the LLM config to the store if it's not already there
			addLLMConfigFromCode({
				name: worker.llmConfigVar,
				llmConfigFromCode: worker.llmConfigFromCode
			});
		}
	}

	// Type-specific mappings
	switch (worker.workerType) {
		case 'taskworker':
			nodeData.requiredMembers = ['consume_work'];
			nodeData.isCached = worker.isCached;
			break;
		case 'llmtaskworker':
			nodeData.isCached = worker.isCached;
			nodeData.requiredMembers = ['prompt', 'system_prompt'];
			nodeData.prompt = worker.classVars?.prompt || '# No prompt found';
			nodeData.system_prompt = worker.classVars?.system_prompt || worker.classVars?.system || '';
			// Map boolean flags directly from classVars (parser still puts them there)
			nodeData.use_xml = worker.classVars?.use_xml || false;
			nodeData.debug_mode = worker.classVars?.debug_mode || false;
			// Explicitly map llm_input_type from classVars
			nodeData.llm_input_type = worker.classVars?.llm_input_type || '';
			nodeData.llm_output_type = worker.classVars?.llm_output_type || '';
			break;
		case 'joinedtaskworker':
			// Map the join_type from class variables
			nodeData.join_type = worker.classVars?.join_type || ''; // Use extracted join_type or default to empty
			nodeData.requiredMembers = ['consume_work_joined'];
			break;
		case 'subgraphworker':
			console.log('SubGraphWorker found:', worker);
			// Store factory details if present
			nodeData.isFactoryCreated = !!worker.factoryFunction;
			nodeData.factoryFunction = worker.factoryFunction;
			nodeData.factoryInvocation = worker.factoryInvocation;
			break;
		// Add other worker types if needed
	}
	return nodeData;
}
