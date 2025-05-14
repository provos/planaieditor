import type { Writable } from 'svelte/store';
import type { Node } from '@xyflow/svelte';
import { getDefaultMethodBody } from './defaults';
import { debounceWithID } from './utils';
import type { DataInputNodeData } from '$lib/components/nodes/DataInputNode.svelte';
import type { NodeData } from '$lib/components/nodes/TaskNode.svelte';
import { generateUniqueName } from '$lib/utils/utils';
import { allClassNames } from '$lib/stores/classNameStore';
import type { XYPosition } from '@xyflow/svelte';

// Adds a method to the node with the given id
export function addAvailableMethod(nodes: Writable<Node[]>, id: string, methodName: string) {
    nodes.update((currentNodes) => {
        return currentNodes.map((node) => {
            if (node.id === id) {
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
}

// Persists the given data for the node with the given id - overwrites the existing data
// The 'id' parameter is now first to be compatible with debounceWithID
function persistNodeData(id: string, nodes: Writable<Node[]>, data: Record<string, any>) {
    nodes.update((currentNodes) => {
        return currentNodes.map((node) => {
            if (node.id === id) {
                // We completely replace the node's data object with the new data, because
                // we need to support deleting data from the node's data object.
                return { ...node, data: { ...data } };
            }
            return node;
        });
    });
}

// Find DataInput nodes that have a single field that is of type string
export function findDataInputForAssistant(nodes: Node[]): Node | null {
    const dataInputNodes = nodes.filter((node) => node.type === 'datainput');
    const classNames: string[] = dataInputNodes
        .map((node) => (node.data as unknown as DataInputNodeData)?.className)
        .filter((className): className is string => className === "ChatTask");
    if (classNames.length != 1) {
        return null;
    }

    const taskNodes: Node[] = nodes.filter(
        (node) =>
            (node.type === 'taskimport') &&
            (node.data as unknown as NodeData)?.className === "ChatTask" &&
            (node.data as unknown as NodeData)?.fields.length == 1 &&
            (node.data as unknown as NodeData)?.fields[0].type === 'ChatMessage' &&
            (node.data as unknown as NodeData)?.fields[0].isList
    );

    if (taskNodes.length != 1) {
        return null;
    }

    return dataInputNodes[0];
}

export function isWorkerTypeNode(node: Node): boolean {
    return node.type === 'taskworker' || node.type === 'llmtaskworker' || node.type === 'joinedtaskworker' || node.type === 'subgraphworker' || node.type === 'chattaskworker';
}

export function nodeDataFromType(id: string, nodeType: string): any {
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
        case 'modulelevelimport': {
            nodeData = {
                code: '# Add your module level imports here',
                nodeId: id
            };
            break;
        }
        case 'taskworker': {
            const baseName = 'TaskWorker'; // Use base name for uniqueness check
            const uniqueName = generateUniqueName(baseName, existingNames);
            nodeData = {
                workerName: uniqueName, // Assign the unique name
                requiredMembers: ['consume_work'],
                entryPoint: false,
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
                requiredMembers: ['prompt', 'system_prompt'],
                entryPoint: false,
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
                requiredMembers: ['consume_work_joined'],
                entryPoint: false,
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
                entryPoint: false,
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
                entryPoint: false,
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
        case 'dataoutput': {
            const baseName = 'DataOutput';
            const uniqueName = generateUniqueName(baseName, existingNames);
            nodeData = {
                workerName: uniqueName,
                nodeId: id,
                receivedData: [],
                inputTypes: []
            };
            break;
        }
        default:
            console.log(`Unknown node type: ${nodeType}`);
            return;
    }
    
    return nodeData;
}

export function addNewNode(
    nodes: Writable<Node[]>, id: string, nodeType: string, position: XYPosition, nodeData: any) {
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

// Debounce the persistNodeData function to avoid excessive updates to the nodes store.
// debounceWithID will use the first argument of persistNodeData (the 'id') as the key.
export const persistNodeDataDebounced = debounceWithID(persistNodeData, 1000);
