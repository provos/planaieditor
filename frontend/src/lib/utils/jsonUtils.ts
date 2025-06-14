import type { Node, Edge } from '@xyflow/svelte';
import { get } from 'svelte/store';
import { nodes as nodesStore, edges as edgesStore } from '$lib/stores/graphStore';
import {
	llmConfigs as llmConfigsStore,
	llmConfigsFromCode as llmConfigsFromCodeStore
} from '$lib/stores/llmConfigsStore';
import type { LLMConfig, LLMConfigFromCode } from '$lib/stores/llmConfigsStore';
import { graphName as graphNameStore } from '$lib/stores/graphNameStore.svelte';
import { downloadFile } from '$lib/utils/utils';
import { clearAssistantMessages } from '$lib/stores/assistantStateStore.svelte';
import { getEdgeStyleProps } from '$lib/utils/edgeUtils';
import type { ExportStatus } from '$lib/utils/pythonExport';
import { tools as toolStore, type Tool as ToolType } from '$lib/stores/toolStore.svelte';
import {
	tasks as taskStore,
	type Task as TaskType,
	type Field as FieldType
} from '$lib/stores/taskStore.svelte';
import {
	taskImports as taskImportsStore,
	type TaskImport as TaskImportType
} from '$lib/stores/taskImportStore.svelte';

export interface SavedGraphState {
	version: number;
	name?: string;
	nodes: Node[];
	edges: Edge[];
	tools: ToolType[];
	tasks: TaskType[];
	taskImports: TaskImportType[];
	llmConfigs: LLMConfig[];
	llmConfigsFromCode: LLMConfigFromCode[];
}

export function saveGraphToJson() {
	const currentNodes = get(nodesStore);
	const currentEdges = get(edgesStore);
	const currentUserLLMConfigs = get(llmConfigsStore);
	const currentCodeLLMConfigs = get(llmConfigsFromCodeStore);
	const currentGraphNameValue = get(graphNameStore);

	const graphState: SavedGraphState = {
		version: 2,
		name: currentGraphNameValue,
		nodes: currentNodes,
		edges: currentEdges,
		tools: toolStore,
		tasks: taskStore,
		taskImports: taskImportsStore,
		llmConfigs: currentUserLLMConfigs,
		llmConfigsFromCode: currentCodeLLMConfigs
	};

	const jsonString = JSON.stringify(graphState, null, 2);
	downloadFile(`${currentGraphNameValue || 'planai-graph'}.json`, jsonString);

	console.log('Graph saved to JSON.');
}

async function clearGraph() {
	nodesStore.set([]);
	edgesStore.set([]);
	llmConfigsStore.set([]);
	llmConfigsFromCodeStore.set([]);
	toolStore.length = 0;
	taskStore.length = 0;
	taskImportsStore.length = 0;
	clearAssistantMessages();
	graphNameStore.set('');
	await new Promise((resolve) => setTimeout(resolve, 10));
}

export async function loadGraphFromJson(jsonContent: string): Promise<ExportStatus> {
	await clearGraph();

	try {
		const loadedState: SavedGraphState = JSON.parse(jsonContent);

		switch (loadedState.version) {
			case 1:
				// Tools did not exist in version 1
				if (!loadedState.tools) {
					loadedState.tools = [];
				}
				if (!loadedState.tasks) {
					loadedState.tasks = [];
				}
				if (!loadedState.taskImports) {
					loadedState.taskImports = [];
				}

				// Convert task nodes to the task store
				const taskNodes = loadedState.nodes.filter((node) => node.type === 'task');
				taskNodes.forEach((node) => {
					const task: TaskType = {
						id: node.id,
						className: node.data.className as string,
						type: 'task',
						fields: node.data.fields as FieldType[]
					};
					loadedState.tasks.push(task);
				});

				// Convert taskimport nodes to the taskimport store
				const taskImportNodes = loadedState.nodes.filter((node) => node.type === 'taskimport');
				taskImportNodes.forEach((node) => {
					const taskImport: TaskImportType = {
						id: node.id,
						type: 'taskimport',
						className: node.data.className as string,
						fields: node.data.fields as FieldType[],
						modulePath: node.data.modulePath as string,
						isImplicit: node.data.isImplicit as boolean,
						availableClasses: node.data.availableClasses as string[]
					};
					loadedState.taskImports.push(taskImport);
				});

				// Remove task nodes from the graph
				loadedState.nodes = loadedState.nodes.filter(
					(node) => node.type !== 'task' && node.type !== 'taskimport'
				);

				// Convert old output handle IDs from output-{typename} to output-{id}
				loadedState.edges = loadedState.edges.map((edge) => {
					if (edge.sourceHandle && edge.sourceHandle.startsWith('output-')) {
						const typeName = edge.sourceHandle.substring(7); // Remove 'output-' prefix

						// Find the task by class name to get its ID
						const task =
							loadedState.tasks.find((t) => t.className === typeName) ||
							loadedState.taskImports.find((t) => t.className === typeName);

						if (task) {
							// Update the handle ID to use the task ID instead of class name
							return {
								...edge,
								sourceHandle: `output-${task.id}`
							};
						}
					}
					return edge;
				});
				break;
			case 2:
				break;
			default:
				throw new Error('Unsupported graph version.');
		}
		if (
			!loadedState ||
			typeof loadedState !== 'object' ||
			!Array.isArray(loadedState.nodes) ||
			!Array.isArray(loadedState.edges) ||
			!Array.isArray(loadedState.llmConfigs) ||
			!Array.isArray(loadedState.llmConfigsFromCode) ||
			!Array.isArray(loadedState.tools) ||
			!Array.isArray(loadedState.tasks) ||
			!Array.isArray(loadedState.taskImports)
		) {
			throw new Error('Invalid JSON file structure.');
		}

		taskStore.push(...loadedState.tasks);
		taskImportsStore.push(...loadedState.taskImports);
		toolStore.push(...loadedState.tools);
		nodesStore.set(loadedState.nodes);
		edgesStore.set(loadedState.edges);
		llmConfigsStore.set(loadedState.llmConfigs);
		llmConfigsFromCodeStore.set(loadedState.llmConfigsFromCode);
		if (loadedState.name) {
			graphNameStore.set(loadedState.name);
		}

		edgesStore.update((eds) => {
			return eds.map((edge) => {
				const sourceNode = get(nodesStore).find((node) => node.id === edge.source);
				if (!sourceNode) {
					console.error('sourceNode not found during edge style update in loadGraphFromJson');
					return edge;
				}
				const styleProps = getEdgeStyleProps(sourceNode, edge);
				return { ...edge, style: styleProps.style, animated: styleProps.animated };
			});
		});

		return { type: 'success', message: 'Graph loaded successfully.' };
	} catch (error: any) {
		console.error('Error loading graph from JSON:', error);
		await clearGraph();
		return {
			type: 'error',
			message: `Load failed: ${error.message || 'Invalid JSON format'}`
		};
	}
}
