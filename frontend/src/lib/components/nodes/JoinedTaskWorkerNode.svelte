<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import { allClassNames } from '$lib/stores/classNameStore'; // Import store for worker names
	import { get } from 'svelte/store'; // To get store value
	import { useStore, useUpdateNodeInternals } from '@xyflow/svelte';
	import type { Node, Edge } from '@xyflow/svelte';
	import { tick } from 'svelte';

	// Extend the base data interface
	interface JoinedWorkerData extends BaseWorkerData {
		join_type: string; // Class name of the worker to join on
		// consume_work_joined is now handled within methods
	}

	let { id, data } = $props<{
		id: string;
		data: JoinedWorkerData;
	}>();

	// Ensure default methods are initialized
	const defaultConsumeWorkJoined = `    # Process the list of input tasks and produce output
    # Example: self.publish_work(output_task, input_task=tasks[0])
    pass`;

	if (!data.methods) {
		data.methods = {};
	}
	if (!data.methods.consume_work_joined) {
		data.methods.consume_work_joined = defaultConsumeWorkJoined;
	}
	if (!data.join_type) {
		data.join_type = ''; // Initialize if not present
	}

	const { nodes, edges } = useStore(); // Access the nodes and edges stores
	const updateNodeInternals = useUpdateNodeInternals(); // Initialize the hook

	// State for editing join_type
	let availableWorkerClasses = $state<string[]>([]);
	let joinedInputType = $state<string>(''); // Derived input type for consume_work_joined

	// Local state for join_type
	let joinType = $state(data.join_type);

	// Combine hardcoded option with dynamic ones
	let allJoinTypeOptions = $derived(['InitialTaskWorker', ...availableWorkerClasses]);

	// Get available worker names from the store
	$effect(() => {
		const unsub = allClassNames.subscribe((nameMap) => {
			const workers: string[] = [];
			const currentNodes = get(nodes); // Get current nodes directly from the nodes store
			nameMap.forEach((name, nodeId) => {
				const node = currentNodes.find((n: Node) => n.id === nodeId); // Add type annotation
				// Check if it's a worker type (excluding self) and has a name
				if (node && node.type !== 'task' && node.id !== id && name) {
					workers.push(name);
				}
			});
			availableWorkerClasses = workers;
		});
		return unsub;
	});

	// Update derived input type based on incoming edges
	$effect(() => {
		let currentNodes: Node[] = [];
		let currentEdges: Edge[] = [];

		const unsubNodes = nodes.subscribe((nodesValue: Node[]) => (currentNodes = nodesValue || [])); // Use nodes store directly
		const unsubEdges = edges.subscribe((edgesValue: Edge[]) => (currentEdges = edgesValue || [])); // Use edges store directly

		const incomingEdges = currentEdges.filter((edge: Edge) => edge.target === id);
		const sourceNodeIds = incomingEdges.map((edge: Edge) => edge.source);
		const sourceClassNames: string[] = sourceNodeIds
			.map((nodeId: string) => {
				const sourceNode = currentNodes.find((node: Node) => node.id === nodeId);
				const edge = incomingEdges.find((e) => e.source === nodeId);
				const sourceHandleId = edge?.sourceHandle;
				if (sourceHandleId && sourceHandleId.startsWith('output-')) {
					return sourceHandleId.substring(7);
				}
				return sourceNode?.data?.className; // Primarily from Task nodes
			})
			.filter(Boolean) as string[];

		// Use the first identified unique input type for the signature
		const uniqueInputs = [...new Set(sourceClassNames)];
		joinedInputType = uniqueInputs[0] || 'Task'; // Default to 'Task' if no input connected

		// Cleanup
		return () => {
			unsubNodes();
			unsubEdges();
		};
	});

	// Sync local joinType state back to data prop
	$effect(() => {
		data.join_type = joinType;
	});

	// Sync data prop changes to local state (e.g., on import)
	$effect(() => {
		joinType = data.join_type;
	});

	// Update code in the data object
	function handleCodeUpdate(newCode: string) {
		data.methods.consume_work_joined = newCode;
	}

	// Compute the title for the code section
	let consumeWorkJoinedTitle = $derived(
		`def consume_work_joined(self, tasks: list[${joinedInputType}]):`
	);

	async function handleCollapse() {
		await tick();
		updateNodeInternals(id);
	}
</script>

<BaseWorkerNode {id} {data} defaultName="JoinedTaskWorker" minHeight={220}>
	<!-- Join Type Section -->
	<div class="mb-2 flex-none px-1">
		<h3 class="text-2xs mb-1 font-semibold text-gray-600">Join Type</h3>
		<!-- Always visible dropdown -->
		<select
			class="text-2xs mt-1 w-full rounded border border-gray-200 px-1 py-0.5"
			bind:value={joinType}
		>
			<option value="">Select join type...</option>
			{#each allJoinTypeOptions as workerName (workerName)}
				<option value={workerName}>{workerName}</option>
			{/each}
		</select>
	</div>

	<!-- Code Section for consume_work_joined -->
	<div class="flex min-h-0 flex-grow flex-col overflow-hidden px-1 pb-1">
		<EditableCodeSection
			title={consumeWorkJoinedTitle}
			code={data.methods.consume_work_joined}
			language="python"
			onUpdate={handleCodeUpdate}
			showReset={true}
			initialCollapsed={false}
			onCollapseToggle={handleCollapse}
		/>
	</div>
</BaseWorkerNode>

<style>
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
