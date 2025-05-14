import type { Writable } from 'svelte/store';
import type { Node } from '@xyflow/svelte';
import { getDefaultMethodBody } from './defaults';
import { debounceWithID } from './utils';
import type { DataInputNodeData } from '$lib/components/nodes/DataInputNode.svelte';
import type { NodeData } from '$lib/components/nodes/TaskNode.svelte';

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
export function findDataInputNodesWithSingleStringField(nodes: Node[]) {
    const dataInputNodes = nodes.filter((node) => node.type === 'datainput');
    const classNames: string[] = dataInputNodes
        .map((node) => (node.data as unknown as DataInputNodeData).className)
        .filter((className): className is string => className !== null);
    const taskNodes: Node[] = nodes.filter(
        (node) =>
            (node.type === 'task' || node.type === 'taskimport') &&
            classNames.includes((node.data as unknown as NodeData).className) &&
            (node.data as unknown as NodeData).fields.length == 1 &&
            (node.data as unknown as NodeData).fields[0].type === 'string'
    );
    const taskNodeNames: string[] = taskNodes.map((node) => (node.data as unknown as NodeData).className);

    const dataInputNodesWithSingleStringField = dataInputNodes.filter((node) => {
        const data = node.data as unknown as DataInputNodeData;
        return data.className !== null && taskNodeNames.includes(data.className);
    });
    return dataInputNodesWithSingleStringField;
}

export function isWorkerTypeNode(node: Node): boolean {
    return node.type === 'taskworker' || node.type === 'llmtaskworker' || node.type === 'joinedtaskworker' || node.type === 'subgraphworker' || node.type === 'chattaskworker';
}

// Debounce the persistNodeData function to avoid excessive updates to the nodes store.
// debounceWithID will use the first argument of persistNodeData (the 'id') as the key.
export const persistNodeDataDebounced = debounceWithID(persistNodeData, 1000);
