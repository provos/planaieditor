import { llmConfigs, type LLMConfig } from '$lib/stores/llmConfigsStore';
import { taskImports as taskImportStore } from '$lib/stores/taskImportStore.svelte';
import { tasks as taskStore } from '$lib/stores/taskStore.svelte';
import { tools as toolStore, type Tool } from '$lib/stores/toolStore.svelte';
import type { Edge, Node } from '@xyflow/svelte';
import type { Socket } from 'socket.io-client';
import { get } from 'svelte/store';
import type { BackendError } from './pythonImport';

// Type for export status updates
export interface ExportStatus {
	type: 'idle' | 'loading' | 'success' | 'error';
	message: string;
	python_code?: string;
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
	edges: Edge[],
	mode: 'export' | 'execute' = 'execute'
): ExportStatus {
	if (!socket || !socket.connected) {
		console.error('Socket not connected. Cannot export.');
		return { type: 'error', message: 'Not connected to backend.' };
	}

	// --- Transformation Step ---
	const graphData = convertGraphtoJSON(nodes, edges, mode);

	console.log('Exporting transformed graph:', graphData);

	socket.emit('export_graph', graphData);
	return { type: 'loading', message: 'Exporting...' };
}

interface GraphData {
	nodes: { id: string; data: any }[];
	edges: { source: string; target: string }[];
	mode: 'export' | 'execute' | undefined;
}

function convertLLMConfigToBackendFormat(config: LLMConfig): Record<string, any> {
	const convertedConfig: Record<string, any> = {};

	// Process each property in the config object
	Object.entries(config).forEach(([key, value]) => {
		console.log('key:', key, 'value:', value);
		// Skip name and source properties
		// Only emit values that are not undefined
		if (key !== 'name' && key !== 'source' && key !== 'id' && value !== undefined) {
			convertedConfig[key] = { value: value, is_literal: true };
		}
	});

	return convertedConfig;
}

export function convertGraphtoJSON(
	nodes: Node[],
	edges: Edge[],
	mode: 'export' | 'execute' = 'execute'
): GraphData {
	const nodeIdToNameMap = new Map<string, string>();
	nodes.forEach((node) => {
		const data = node.data as any; // Use any for broader compatibility during processing
		const name: string | undefined = data?.className || data?.workerName;
		if (name) {
			nodeIdToNameMap.set(node.id, name);
		}
	});

	// replace workerName with className for worker nodes
	const exportedNodes = nodes.map((node) => {
		return convertNodeData(node);
	});

	// Transform edges to use class names instead of node IDs
	const exportedEdges: Array<{ source: string; target: string }> = edges
		.map((edge) => {
			const sourceName = nodeIdToNameMap.get(edge.source);
			const targetName = nodeIdToNameMap.get(edge.target);
			const sourceNode = nodes.find((n) => n.id === edge.source);

			if (!sourceName || !targetName) {
				console.warn(`Skipping edge ${edge.id}: Could not find names for source/target IDs.`);
				return null; // Mark edge for removal if names aren't found
			}

			// Return new edge structure with names
			// TODO: Potentially include targetInputType if needed by generator?
			return {
				source: sourceNode?.type === 'datainput' ? 'datainput-' + sourceName : sourceName,
				target: targetName
				// targetInputType: ... // If needed
			};
		})
		.filter((edge): edge is { source: string; target: string } => edge !== null); // Type guard to filter out nulls and satisfy TypeScript

	// Send transformed data
	const graphData = {
		nodes: exportedNodes,
		edges: exportedEdges,
		tools: toolStore,
		tasks: taskStore,
		taskimports: taskImportStore,
		mode: mode
	}; // Use transformed nodes and edges
	return graphData;
}

/**
 * Converts a node's data into a format suitable for backend processing.
 *
 * This function handles several transformations:
 * 1. Standardizes workerName to className for worker nodes
 * 2. Processes LLM configurations for LLM/chat task workers, handling both UI-selected and imported configs
 * 3. Consolidates known class variables into a classVars object for worker nodes
 * 4. Cleans up frontend-specific properties
 *
 * @param node The node to process, containing type and data properties
 * @returns A new node object with transformed data
 */
export function convertNodeData(node: Node) {
	const data = node.data as any; // Use any for easier manipulation
	const processedData = { ...data };

	// Standardize workerName to className for worker nodes
	if (data?.workerName) {
		processedData.className = data.workerName;
		delete processedData.workerName;
	}

	// If it's an LLM worker node, handle LLM configuration
	if (node.type === 'llmtaskworker' || node.type === 'chattaskworker') {
		// Priority 1: If user selected an LLM config in the UI, use that
		if (data?.llmConfigName) {
			const configName = data.llmConfigName;
			const allConfigs = get(llmConfigs); // Get current value of the store
			const foundConfig = allConfigs.find((c) => c.name === configName);

			if (foundConfig) {
				// Add the full config object to the data being exported
				const convertConfig = convertLLMConfigToBackendFormat(foundConfig);

				processedData.llmConfig = convertConfig;
				// Remove the name now that we have the full object
				delete processedData.llmConfigName;

				// If there was an imported config, we're now overriding it
				if (processedData.llmConfigFromCode) {
					console.log(`Overriding imported LLM config with user-selected config: ${configName}`);
				}
			} else {
				// Handle case where config name exists but config is not found (shouldn't happen ideally)
				console.warn(
					`LLM Configuration named '${configName}' selected but not found in store. Skipping LLM config export for node ${node.id}`
				);
				// Ensure llmConfig is not present if not found
				delete processedData.llmConfig;
				// Keep llmConfigName? Or delete it? Deleting might be cleaner for backend.
				delete processedData.llmConfigName;
			}
		}

		// Priority 2: If no user-selected config but we have an imported config, use that
		else if (data?.llmConfigFromCode) {
			// The backend expects 'llmConfig' for code generation, so we convert the imported format
			processedData.llmConfig = { ...data.llmConfigFromCode };

			// If host is present, map it to baseUrl
			if (data.llmConfigFromCode.host) {
				processedData.llmConfig.baseUrl = data.llmConfigFromCode.host;
				delete processedData.llmConfig.host;
			}
			delete processedData.llmConfigFromCode;
			console.log(`Using imported LLM config for node ${node.id}`);
		}

		// Convert inputTypes to llm_input_type
		if (data.inputTypes && node.type === 'llmtaskworker') {
			if (!processedData.classVars) {
				processedData.classVars = {};
			}
			processedData.classVars['llm_input_type'] = data.inputTypes[0];
			delete processedData.inputTypes;
			delete processedData.llm_input_type;
		}

		// Clean up display-only properties
		delete processedData.llmConfigDescription;
	}

	// Consolidate known class variables into classVars for worker nodes
	const knownClassVars = [
		'prompt',
		'system_prompt',
		'use_xml',
		'debug_mode',
		'llm_output_type',
		'join_type',
		'output_types',
		'tools'
	];
	if (node.type?.endsWith('worker')) {
		// Apply only to worker node types
		if (!processedData.classVars) {
			processedData.classVars = {};
		}
		for (const key of knownClassVars) {
			if (processedData[key] !== undefined) {
				(processedData.classVars as Record<string, any>)[key] = processedData[key];
				delete processedData[key];
			}
		}

		// If tools were captured, convert them to tool names
		if (processedData.classVars.tools && Array.isArray(processedData.classVars.tools)) {
			const toolNames = processedData.classVars.tools
				.map((toolId: string) => {
					const toolNode = toolStore.find((t: Tool) => t.id === toolId);
					return toolNode ? toolNode.name : null;
				})
				.filter((name: string | null) => name !== null);

			processedData.classVars.tools = toolNames;
		}
	}

	// Handle factory function details for subgraphworkers
	if (node.type === 'subgraphworker' && data?.isFactoryCreated) {
		// Remove isFactoryCreated flag as it's frontend-specific
		delete processedData.isFactoryCreated;
	}

	// ChatTaskWorker is special as it basically doesn't take anything
	if (node.type === 'chattaskworker' && data?.classVars) {
		delete data.classVars.prompt;
	}

	return { ...node, data: processedData };
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
	resultData: {
		success: boolean;
		message?: string;
		error?: BackendError;
		mode?: 'export' | 'execute' | undefined;
		python_code?: string;
		validation_result?: any;
	},
	nodes: Node[]
): { status: ExportStatus; updatedNodes?: Node[] } {
	// First clear any existing errors
	const clearedNodes = clearNodeErrors([...nodes]);

	if (resultData.success) {
		// check if any nodes have errors
		const hasErrors = nodes.some((node) => node.data?.error);
		return {
			status: {
				type: 'success',
				message: resultData.message || 'Export successful!'
			},
			updatedNodes: hasErrors ? clearedNodes : undefined
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
					n.id === targetNode.id ? { ...n, data: { ...n.data, error: errorInfo.message } } : n
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
