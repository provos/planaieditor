import { get } from 'svelte/store';
import { persisted } from 'svelte-persisted-store';
import type { Node, Edge } from '@xyflow/svelte';

export const nodes = persisted<Node[]>('nodes', []);
export const edges = persisted<Edge[]>('edges', []);

export function getCurrentNodes(): Node[] {
	return get(nodes);
}

export function getCurrentEdges(): Edge[] {
	return get(edges);
}
