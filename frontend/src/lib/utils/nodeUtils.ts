import type { Writable } from 'svelte/store';
import type { Node } from '@xyflow/svelte';
import { getDefaultMethodBody } from './defaults';

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
