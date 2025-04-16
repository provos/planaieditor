import type { Node, Edge } from '@xyflow/svelte';
import type { Socket } from 'socket.io-client';
import type { BackendError } from './pythonImport';
// import type { TaskImportNodeData } from '../components/nodes/TaskImportNode.svelte'; // Removed import

// Type for export status updates
export interface ExportStatus {
    type: 'idle' | 'loading' | 'success' | 'error';
    message: string;
}

/**
 * Exports the current graph as Python code by sending it to the backend
 * @param socket Active Socket.io connection to the backend
 * @param nodes Current nodes from the graph
 * @param edges Current edges from the graph
 * @returns Object with status type and message
 */
export function exportPythonCode(
    socket: Socket | null,
    nodes: Node[],
    edges: Edge[]
): ExportStatus {
    if (!socket || !socket.connected) {
        console.error('Socket not connected. Cannot export.');
        return { type: 'error', message: 'Not connected to backend.' };
    }

    // --- Transformation Step ---
    // Create a map from nodeId to className/workerName
    const nodeIdToNameMap = new Map<string, string>();
    nodes.forEach(node => {
        const data = node.data as any; // Use any for broader compatibility during processing
        const name: string | undefined = data?.className || data?.workerName;
        if (name) {
            nodeIdToNameMap.set(node.id, name);
        }
    });

    // replace workerName with className in nodes
    const exportedNodes = nodes.map(node => {
        const data = node.data as any; // Use any for easier manipulation
        let processedData = { ...data };

        // Standardize workerName to className for worker nodes
        if (data?.workerName) {
            processedData.className = data.workerName;
            delete processedData.workerName;
        }

        // Consolidate known class variables into classVars for worker nodes
        const knownClassVars = [
            'prompt',
            'system_prompt',
            'use_xml',
            'debug_mode',
            'llm_input_type',
            'llm_output_type',
            'join_type',
            'output_types'
        ];
        if (node.type?.endsWith('worker')) { // Apply only to worker node types
            if (!processedData.classVars) {
                processedData.classVars = {};
            }
            for (const key of knownClassVars) {
                if (processedData[key] !== undefined) {
                    (processedData.classVars as Record<string, any>)[key] = processedData[key];
                    delete processedData[key];
                }
            }
        }

        if (node.type === 'taskimport') {
            // Explicitly check type before asserting
            const importData = data as { modulePath?: string, className?: string }; // Use inline type
            if (importData.modulePath && importData.className) {
                processedData.importDetails = {
                    modulePath: importData.modulePath,
                    className: importData.className
                };
                // Set the className for dependency mapping
                processedData.className = importData.className;
                // Remove fields that are not needed by the backend generator for this type
                delete processedData.modulePath;
            } else {
                console.warn(`Skipping TaskImportNode ${node.id} due to missing modulePath or className.`);
                // Consider how to handle incomplete import nodes - skip or error?
                // For now, let's keep it but it might cause issues downstream if className isn't set.
            }
        }

        return { ...node, data: processedData };
    });

    // Transform edges to use class names instead of node IDs
    const exportedEdges: Array<{ source: string; target: string }> = edges
        .map(edge => {
            const sourceName = nodeIdToNameMap.get(edge.source);
            const targetName = nodeIdToNameMap.get(edge.target);

            if (!sourceName || !targetName) {
                console.warn(`Skipping edge ${edge.id}: Could not find names for source/target IDs.`);
                return null; // Mark edge for removal if names aren't found
            }

            // Return new edge structure with names
            // TODO: Potentially include targetInputType if needed by generator?
            return {
                source: sourceName,
                target: targetName
                // targetInputType: ... // If needed
            };
        })
        .filter((edge): edge is { source: string; target: string } => edge !== null); // Type guard to filter out nulls and satisfy TypeScript
    // --- End Transformation ---

    // Send transformed data
    const graphData = { nodes: exportedNodes, edges: exportedEdges }; // Use transformed nodes and edges
    console.log('Exporting transformed graph:', graphData);

    socket.emit('export_graph', graphData);
    return { type: 'loading', message: 'Exporting...' };
}

/**
 * Clears error flags from all node data objects
 * @param nodes List of nodes to process
 * @returns Updated list of nodes with errors cleared
 */
export function clearNodeErrors(nodes: Node[]): Node[] {
    return nodes.map((node) => {
        if (node.data?.error) {
            const { error, ...restData } = node.data; // Destructure to remove error
            return { ...node, data: restData };
        } else {
            return node; // No error property to remove
        }
    });
}

/**
 * Processes export results from the backend and updates nodes with any error information
 * @param resultData Export result data from the backend
 * @param nodes Current graph nodes
 * @returns Object containing updated status and nodes with error flags if necessary
 */
export function processExportResult(
    resultData: { success: boolean; message?: string; error?: BackendError },
    nodes: Node[]
): { status: ExportStatus; updatedNodes?: Node[] } {
    // First clear any existing errors
    const clearedNodes = clearNodeErrors([...nodes]);

    if (resultData.success) {
        return {
            status: {
                type: 'success',
                message: resultData.message || 'Export successful!'
            }
        };
    } else {
        const errorInfo = resultData.error;
        if (!errorInfo) {
            return {
                status: {
                    type: 'error',
                    message: 'Unknown export error occurred.'
                }
            };
        }

        console.error(`Export failed: ${errorInfo.message}`, errorInfo.fullTraceback);

        if (errorInfo.nodeName) {
            // Find the node by the name identified in the backend
            const targetNode = clearedNodes.find(
                (n) =>
                    (n.data as any)?.className === errorInfo.nodeName || // Check className
                    (n.data as any)?.workerName === errorInfo.nodeName
            );

            if (targetNode) {
                // Assign the core message to the specific node's data
                const updatedNodes = clearedNodes.map((n) =>
                    n.id === targetNode.id
                        ? { ...n, data: { ...n.data, error: errorInfo.message } }
                        : n
                );

                return {
                    status: {
                        type: 'error',
                        message: `Error in node ${errorInfo.nodeName}: ${errorInfo.message}`
                    },
                    updatedNodes
                };
            } else {
                // Couldn't find node for the name, show generic message with details
                console.warn(`Could not find node with name: ${errorInfo.nodeName}`);
                return {
                    status: {
                        type: 'error',
                        message: `Error (unlinked): ${errorInfo.message}`
                    }
                };
            }
        } else {
            // Show generic error message if backend couldn't identify a node name
            return {
                status: {
                    type: 'error',
                    message: errorInfo.message
                }
            };
        }
    }
}