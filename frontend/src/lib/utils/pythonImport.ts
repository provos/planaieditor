import type { Node } from '@xyflow/svelte';
import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';
import { allClassNames } from '$lib/stores/classNameStore';
import { get } from 'svelte/store';

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
                origin: [0, 0],
                dragHandle: '.custom-drag-handle' // Use the custom drag handle
            };
            newNodes.push(newNode);
            nextY += 180; // Basic vertical spacing
        });

        // --- Create Worker Nodes ---

        // Get existing names to avoid conflicts
        const existingNames = new Set(Object.values(get(allClassNames)));

        importedWorkers.forEach((worker) => {
            // Basic check for name collision (though backend should ideally handle this)
            if (existingNames.has(worker.className)) {
                console.warn(`Worker class name "${worker.className}" already exists. Skipping import for this worker.`);
                return; // Skip this worker
            }

            const id = `imported-${worker.workerType}-${worker.className}-${Date.now()}`;

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
                position: { x: startX + 300, y: nextY }, // Offset workers horizontally
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

        // Update the taskClassNamesStore with the newly imported names
        const importedTaskNames = new Set(importedTasks.map((task) => task.className));
        taskClassNamesStore.update((existingNames) => {
            importedTaskNames.forEach((name) => existingNames.add(name));
            return new Set(existingNames); // Create a new set to trigger reactivity
        });

        return {
            success: true,
            message: `Imported ${importedTasks.length} Task(s) and ${importedWorkers.length} Worker(s).`,
            nodes: newNodes
        };
    } catch (error: any) {
        console.error('Error importing Python code:', error);
        return {
            success: false,
            message: `Import failed: ${error.message || 'Unknown error'}`
        };
    }
}