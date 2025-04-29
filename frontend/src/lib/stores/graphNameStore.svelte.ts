import { persisted } from 'svelte-persisted-store';

export const graphName = persisted<string>('graphName', '');