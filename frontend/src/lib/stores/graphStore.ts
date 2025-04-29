import { persisted } from 'svelte-persisted-store';
import type { Node, Edge } from '@xyflow/svelte';

export const nodes = persisted<Node[]>('nodes', []);
export const edges = persisted<Edge[]>('edges', []);
