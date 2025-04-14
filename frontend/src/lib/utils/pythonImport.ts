import type { Node, Edge } from '@xyflow/svelte';
import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';
import { allClassNames } from '$lib/stores/classNameStore';
import { get } from 'svelte/store';
import ELK from 'elkjs/lib/elk.bundled.js';
import { Position } from '@xyflow/svelte';
import { getColorForType } from '$lib/utils/colorUtils';

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
    className: string;
    workerType: string; // e.g., "taskworker", "llmtaskworker"
    classVars: Record<string, any>; // Dictionary of known parsed class vars
    inputTypes?: string[]; // Optional: Parsed from consume_work type hint
    methods: Record<string, string>; // Dictionary of known method sources
    otherMembersSource: string; // Consolidated source code of other members
}

// Result type for the Python import operation
export interface ImportResult {
    success: boolean;
    message: string;
    nodes?: Node[];
    edges?: Edge[];
    entryEdges?: Array<{ sourceTask: string, targetWorker: string }>;
}

// --- Type for Edges from Backend --- //
export interface ImportedEdge {
    source: string; // Class name of source worker
    target: string; // Class name of target worker
    targetInputType?: string; // Optional: Input type name of the target worker
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
    'elk.direction': 'DOWN'
};

// Minimal fallback dimensions if node size isn't available yet
const MIN_NODE_WIDTH = 150;
const MIN_NODE_HEIGHT = 50;

export async function layoutGraph(nodesToLayout: Node[], edgesToLayout: Edge[], options = elkOptions): Promise<{ nodes: Node[], edges: Edge[] }> {
    const graph = {
        id: 'root',
        layoutOptions: options,
        children: nodesToLayout.map((node) => ({
            ...node,
            targetPosition: Position.Top,
            sourcePosition: Position.Bottom,
            width: node.measured?.width && node.measured.width > 0 ? node.measured.width : MIN_NODE_WIDTH,
            height: node.measured?.height && node.measured.height > 0 ? node.measured.height : MIN_NODE_HEIGHT,
        })),
        // Map Svelte Flow edges to ELK edges
        edges: edgesToLayout.map(edge => ({
            ...edge,
            id: edge.id,
            sources: [edge.source],
            targets: [edge.target]
        })),
    };

    try {
        const layoutedGraph = await elk.layout(graph);
        return {
            nodes: layoutedGraph.children?.map((node) => ({
                ...node,
                // Copy original data back
                data: nodesToLayout.find(n => n.id === node.id)?.data || {},
                // ELK returns x, y; Svelte Flow expects position {x, y}
                position: { x: node.x ?? 0, y: node.y ?? 0 },
            })) ?? [], // Handle cases where children might be undefined

            // Map ELK edges back to Svelte Flow edges
            edges: layoutedGraph.edges?.map(edge => ({
                ...edge,
                id: edge.id,
                source: edge.sources[0],
                target: edge.targets[0]
            })) ?? [],
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
        const response = await fetch('http://localhost:5001/api/import-python', {
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
            throw new Error(`Unexpected response format: ${response.status} ${response.statusText}. Response: ${textError}`);
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
        const importedEntryEdges: Array<{ sourceTask: string, targetWorker: string }> = result.entryEdges || [];

        if (importedTasks.length === 0 && importedWorkers.length === 0) {
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
                origin: [0, 0],
                dragHandle: '.custom-drag-handle' // Use the custom drag handle
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
                console.warn(`Worker class name "${worker.className}" already exists. Skipping import for this worker.`);
                return; // Skip this worker
            }

            const id = `imported-${worker.workerType}-${worker.className}-${Date.now()}`;
            classNameToNodeId[worker.className] = id; // Store mapping

            // Map backend data to frontend node data structure
            const nodeData: any = {
                isCached: worker.workerType.startsWith('cached'), // Set flag based on type
                workerName: worker.className, // Use className as workerName
                nodeId: id,
                // Initialize common fields, specific nodes might override
                inputTypes: worker.inputTypes || [], // Use parsed inputTypes from backend if available
                outputTypes: worker.classVars.output_types || [], // Map output_types
                // Store unparsed methods and members for potential display/editing later
                methods: worker.methods,
                otherMembersSource: worker.otherMembersSource, // Store consolidated source
                classVars: worker.classVars // Store the rest of class vars for now
            };

            // Type-specific mappings
            switch (worker.workerType) {
                case 'taskworker':
                case 'cachedtaskworker':
                    break;
                case 'llmtaskworker':
                case 'cachedllmtaskworker': // Treat similarly for basic import
                    nodeData.prompt = worker.classVars.prompt || '# No prompt found';
                    nodeData.systemPrompt =
                        worker.classVars.system_prompt || worker.classVars.system || '';
                    break;
                case 'joinedtaskworker':
                    // Add specific data mapping for JoinedTaskWorker if needed in the future
                    break;
                // Add other worker types if needed
            }

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
                origin: [0, 0],
                dragHandle: '.custom-drag-handle'
            };
            newNodes.push(newNode);
            nextY += 180; // Basic vertical spacing (adjust as needed)
        });

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
                    target: targetNodeId,
                };
                // If the target has a specific input type, connect to the corresponding source handle
                if (edge.targetInputType) {
                    svelteEdge.sourceHandle = `output-${edge.targetInputType}`;
                }
                // If targetInputType is not specified, sourceHandle remains undefined,
                // connecting to the default source handle (if one exists).
                newEdges.push(svelteEdge);
            } else {
                console.warn(`Could not create edge for ${edge.source} -> ${edge.target}: Node ID not found.`);
            }
        });

        // --- Create Entry Point Edges --- //
        importedEntryEdges.forEach((entryEdge) => {
            const sourceNodeId = classNameToNodeId[entryEdge.sourceTask];   // Source is the Task node
            const targetNodeId = classNameToNodeId[entryEdge.targetWorker]; // Target is the Worker node

            if (sourceNodeId && targetNodeId) {
                const edgeId = `imported-entry-edge-${sourceNodeId}-${targetNodeId}`;
                newEdges.push({
                    id: edgeId,
                    source: sourceNodeId,
                    target: targetNodeId,
                    animated: true
                });
            } else {
                console.warn(`Could not create entry edge for ${entryEdge.sourceTask} -> ${entryEdge.targetWorker}: Node ID not found.`);
            }
        });

        // --- Apply Edge Styling based on Source Task Type ---
        const finalEdges = newEdges.map(svelteEdge => {
            const sourceNode = newNodes.find(n => n.id === svelteEdge.source);
            if (!sourceNode) return svelteEdge; // Should not happen if ID was found before

            let taskType: string | undefined = undefined;
            if (sourceNode.type === 'task') {
                taskType = (sourceNode.data as any)?.className;
            } else if (svelteEdge.sourceHandle && svelteEdge.sourceHandle.startsWith('output-')) {
                taskType = svelteEdge.sourceHandle.split('-')[1];
            } else if (sourceNode.data && Array.isArray(sourceNode.data.outputTypes) && sourceNode.data.outputTypes.length === 1) {
                taskType = sourceNode.data.outputTypes[0];
            }

            let styleString = 'stroke-width:3;'; // Default thickness
            if (taskType) {
                const color = getColorForType(taskType);
                styleString += `stroke:${color};`; // Add color if type found
            }

            return {
                ...svelteEdge,
                style: styleString
            };
        });

        // Update the taskClassNamesStore with the newly imported names
        const importedTaskNames = new Set(importedTasks.map((task) => task.className));
        taskClassNamesStore.update((existingNames) => {
            importedTaskNames.forEach((name) => existingNames.add(name));
            return new Set(existingNames); // Create a new set to trigger reactivity
        });

        return {
            success: true,
            message: `Imported ${importedTasks.length} Task(s) and ${importedWorkers.length} Worker(s).`,
            nodes: newNodes,      // Return original nodes (without layout positions yet)
            edges: newEdges       // Return original edges
        };
    } catch (error: any) {
        console.error('Error importing Python code:', error);
        return {
            success: false,
            message: `Import failed: ${error.message || 'Unknown error'}`
        };
    }
}