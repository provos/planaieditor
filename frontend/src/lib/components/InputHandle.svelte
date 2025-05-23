<script lang="ts">
	import { Handle, Position, useStore } from '@xyflow/svelte';
	import type { Node, Edge } from '@xyflow/svelte';

	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import { getColorForType } from '$lib/utils/colorUtils';
	import { onMount } from 'svelte';

	let { id, data, manuallySelectedInputType, isEditable, onUpdate } = $props<{
		id: string;
		data: BaseWorkerData;
		manuallySelectedInputType: string | null;
		isEditable: boolean;
		onUpdate: (inferredInputTypes: string[]) => void;
	}>();

	let inferredInputTypes = $derived<string[]>(data.inputTypes || []);
	let entryPoint = $derived(data.entryPoint || false);

	const store = useStore();

	let handleColor = $derived(
		getColorForType(
			inferredInputTypes && inferredInputTypes.length > 0 ? inferredInputTypes[0] : ''
		)
	);

	let handleStyle = $derived.by(() => {
		if (entryPoint) {
			// Triangle style for entry point - larger
			return `width: 0; height: 0; border-top: 16px solid transparent; border-bottom: 16px solid transparent; border-left: 20px solid ${handleColor}; background-color: transparent; border-radius: 0; left: -10px; border-right: none;`;
		} else {
			// Default square style
			return `background-color: ${handleColor};`;
		}
	});

	if (isEditable) {
		$effect(() => {
			if (manuallySelectedInputType && inferredInputTypes.length === 0) {
				inferredInputTypes = [manuallySelectedInputType];
				data.inputTypes = [manuallySelectedInputType];
				onUpdate([manuallySelectedInputType]);
			}
		});
	}

	// --- Effects for Reactivity ---
	onMount(() => {
		if (!isEditable) {
			return;
		}

		let currentNodes: Node[] = [];
		let currentEdges: Edge[] = [];

		// Subscribe to nodes store changes
		const unsubNodes = store.nodes.subscribe((nodesValue: Node[]) => {
			currentNodes = nodesValue || [];
			updateInferredTypes(currentNodes, currentEdges);
		});

		// Subscribe to edges store changes
		const unsubEdges = store.edges.subscribe((edgesValue: Edge[]) => {
			currentEdges = edgesValue || [];
			updateInferredTypes(currentNodes, currentEdges);
		});

		// Initial update in case stores already have values
		updateInferredTypes(currentNodes, currentEdges);

		// Cleanup function
		return () => {
			unsubNodes();
			unsubEdges();
		};
	});

	// Function to calculate and update inferred input types
	function updateInferredTypes(nodes: Node[], edges: Edge[]) {
		if (!edges || !nodes) {
			inferredInputTypes = manuallySelectedInputType ? [manuallySelectedInputType] : [];
			return;
		}

		const incomingEdges = edges.filter((edge: Edge) => edge.target === id);
		const sourceNodeIds = incomingEdges.map((edge: Edge) => edge.source);
		const sourceClassNames: string[] = sourceNodeIds
			.map((nodeId: string) => {
				const sourceNode = nodes.find((node: Node) => node.id === nodeId);
				const edge = incomingEdges.find((e) => e.source === nodeId);
				const sourceHandleId = edge?.sourceHandle;
				if (sourceHandleId && sourceHandleId.startsWith('output-')) {
					return sourceHandleId.substring(7);
				}
				// Fallback if handle ID is missing/unexpected
				return sourceNode?.data?.className;
			})
			.filter(Boolean) as string[];

		// make sourceClassNames unique
		const uniqueSourceClassNames = [...new Set(sourceClassNames)];
		if (uniqueSourceClassNames.length === 0 && manuallySelectedInputType) {
			uniqueSourceClassNames.push(manuallySelectedInputType);
		}

		// Update only if there are changes in the inferred input types
		if (
			uniqueSourceClassNames.length !== inferredInputTypes.length ||
			uniqueSourceClassNames.some((type, index) => type !== inferredInputTypes[index])
		) {
			inferredInputTypes = uniqueSourceClassNames;
			data.inputTypes = uniqueSourceClassNames;
			onUpdate(uniqueSourceClassNames);
		}
	}
</script>

<Handle type="target" position={Position.Left} id="input" style={handleStyle} />
