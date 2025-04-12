import type { Node, Edge } from '@xyflow/svelte';
import type { Socket } from 'socket.io-client';
import type { BackendError } from './pythonImport';

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

    const graphData = { nodes, edges };
    console.log('Exporting graph:', graphData);

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
 * @param data Export result data from the backend
 * @param nodes Current graph nodes
 * @returns Object containing updated status and nodes with error flags if necessary
 */
export function processExportResult(
    data: { success: boolean; message?: string; error?: BackendError },
    nodes: Node[]
): { status: ExportStatus; updatedNodes?: Node[] } {
    // First clear any existing errors
    const clearedNodes = clearNodeErrors([...nodes]);

    if (data.success) {
        return {
            status: {
                type: 'success',
                message: data.message || 'Export successful!'
            }
        };
    } else {
        const errorInfo = data.error;
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
                    n.data?.className === errorInfo.nodeName ||
                    n.data?.workerName === errorInfo.nodeName
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