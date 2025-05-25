<script lang="ts">
	import { Handle, Position, useStore } from '@xyflow/svelte';
	import type { Node, Edge } from '@xyflow/svelte';

	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import { getColorForType } from '$lib/utils/colorUtils';
	import { getTaskById } from '$lib/stores/taskStore.svelte';
	import { getTaskImportById } from '$lib/stores/taskImportStore.svelte';
	import { onMount } from 'svelte';
	import { inferInputTypeFromName, type InputType } from '$lib/utils/nodeUtils';

	let { id, data, manuallySelectedInputType, isEditable, onUpdate } = $props<{
		id: string;
		data: BaseWorkerData;
		manuallySelectedInputType: string | null;
		isEditable: boolean;
		onUpdate: (inferredInputTypes: InputType[]) => void;
	}>();

	let inferredInputTypes = $derived<InputType[]>(
		data.inputTypes?.map((className: string) => ({
			className,
			id: '' // We'll need to find the actual ID when we have one
		})) || []
	);
	let entryPoint = $derived(data.entryPoint || false);

	const store = useStore();

	let handleColor = $derived(
		getColorForType(
			inferredInputTypes && inferredInputTypes.length > 0 ? inferredInputTypes[0].className : ''
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
				// Find the task by class name to get the ID
				const newInferredType = inferInputTypeFromName(manuallySelectedInputType);
				inferredInputTypes = [newInferredType];
				data.inputTypes = [newInferredType.className];
				onUpdate([newInferredType]);
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
			if (manuallySelectedInputType) {
				const inferredType = inferInputTypeFromName(manuallySelectedInputType);
				inferredInputTypes = [inferredType];
			} else {
				inferredInputTypes = [];
			}
			return;
		}

		const incomingEdges = edges.filter((edge: Edge) => edge.target === id);
		const sourceClassNames: InputType[] = [];

		for (const edge of incomingEdges) {
			const sourceHandleId = edge.sourceHandle;
			if (sourceHandleId && sourceHandleId.startsWith('output-')) {
				// Extract the task/taskimport ID from the handle
				const taskId = sourceHandleId.substring(7); // Remove 'output-' prefix

				// Look up the task by ID to get the className
				const task = getTaskById(taskId) || getTaskImportById(taskId);
				if (task) {
					sourceClassNames.push({
						className: task.className,
						id: task.id
					});
				}
			}
		}

		// Make sourceClassNames unique by ID
		const uniqueSourceClassNames = sourceClassNames.filter(
			(item, index, self) => index === self.findIndex((t) => t.id === item.id)
		);

		if (uniqueSourceClassNames.length === 0 && manuallySelectedInputType) {
			uniqueSourceClassNames.push(inferInputTypeFromName(manuallySelectedInputType));
		}

		// Update only if there are changes in the inferred input types
		if (
			uniqueSourceClassNames.length !== inferredInputTypes.length ||
			uniqueSourceClassNames.some(
				(type, index) =>
					!inferredInputTypes[index] ||
					type.className !== inferredInputTypes[index].className ||
					type.id !== inferredInputTypes[index].id
			)
		) {
			inferredInputTypes = uniqueSourceClassNames;
			data.inputTypes = inferredInputTypes.map((type) => type.className);
			onUpdate(inferredInputTypes);
		}
	}
</script>

<Handle type="target" position={Position.Left} id="input" style={handleStyle} />
