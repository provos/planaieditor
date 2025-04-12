import type { Node } from '@xyflow/svelte';
import { taskClassNamesStore } from '$lib/stores/taskClassNamesStore';

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

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Import failed on the backend.');
        }

        const importedTasks: ImportedTask[] = result.tasks || [];

        if (importedTasks.length === 0) {
            return {
                success: true,
                message: 'No Task classes found in the file.'
            };
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
                origin: [0, 0],
                dragHandle: '.custom-drag-handle' // Use the custom drag handle
            };
            newNodes.push(newNode);
            nextY += 180; // Basic vertical spacing
        });

        // Update the taskClassNamesStore with the newly imported names
        const importedTaskNames = new Set(importedTasks.map((task) => task.className));
        taskClassNamesStore.update((existingNames) => {
            importedTaskNames.forEach((name) => existingNames.add(name));
            return new Set(existingNames); // Create a new set to trigger reactivity
        });

        return {
            success: true,
            message: `Successfully imported ${newNodes.length} Task node(s).`,
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