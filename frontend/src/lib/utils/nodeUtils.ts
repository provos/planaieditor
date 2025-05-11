import type { Writable } from 'svelte/store';
import type { Node } from '@xyflow/svelte';
import { getDefaultMethodBody } from './defaults';
import { debounceWithID } from './utils';

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

// Debounce the persistNodeData function to avoid excessive updates to the nodes store.
// debounceWithID will use the first argument of persistNodeData (the 'id') as the key.
export const persistNodeDataDebounced = debounceWithID(persistNodeData, 1000);
