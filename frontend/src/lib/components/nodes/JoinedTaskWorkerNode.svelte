<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import { allWorkerClassNames } from '$lib/stores/classNameStore.svelte'; // Import store for worker names
	import { get } from 'svelte/store'; // To get store value
	import { useStore, useUpdateNodeInternals } from '@xyflow/svelte';
	import type { Node, Edge } from '@xyflow/svelte';
	import { tick } from 'svelte';
	import { persistNodeDataDebounced, isWorkerTypeNode } from '$lib/utils/nodeUtils';
	import { openFullScreenEditor } from '$lib/stores/fullScreenEditorStore.svelte';

	// Extend the base data interface
	export interface JoinedWorkerData extends BaseWorkerData {
		join_type: string; // Class name of the worker to join on
	}

	let { id, data } = $props<{
		id: string;
		data: JoinedWorkerData;
	}>();

	// Ensure default methods are initialized
	const defaultConsumeWorkJoined = `    # Process the list of input tasks and produce output
    # Example: self.publish_work(output_task, input_task=tasks[0])
    pass`;

	const { nodes, edges } = useStore(); // Access the nodes and edges stores
	const updateNodeInternals = useUpdateNodeInternals(); // Initialize the hook

	if (!data.requiredMembers) {
		data.requiredMembers = ['consume_work_joined'];
		persistNodeDataDebounced();
	}

	if (!data.methods) {
		data.methods = {};
		persistNodeDataDebounced();
	}
	if (!data.methods.consume_work_joined) {
		data.methods.consume_work_joined = defaultConsumeWorkJoined;
		persistNodeDataDebounced();
	}
	if (!data.join_type) {
		data.join_type = ''; // Initialize if not present
		persistNodeDataDebounced();
	}

	// State for editing join_type
	let joinedInputType = $state<string>(''); // Derived input type for consume_work_joined
	let availableWorkerClasses = $state<string[]>([]);

	// Local state for join_type
	let joinType = $state(data.join_type);

	// Reactively update availableWorkerClasses when nodes or allClassNames change
	$effect(() => {
		let currentNodes: Node[] = [];

		// Subscribe to nodes store to track changes
		const unsubNodes = nodes.subscribe((nodesValue: Node[]) => {
			currentNodes = nodesValue || [];

			// Recompute workers whenever nodes change
			const workers: string[] = [];

			// Iterate through allClassNames to find worker nodes
			// This access to allClassNames creates reactive dependency
			allWorkerClassNames.forEach((name, nodeId) => {
				const node = currentNodes.find((n: Node) => n.id === nodeId);
				// Check if it's a worker type (excluding self) and has a name
				if (node && isWorkerTypeNode(node) && node.id !== id && name) {
					workers.push(name);
				}
			});

			availableWorkerClasses = workers;
		});

		// Return cleanup function
		return unsubNodes;
	});

	// Combine hardcoded option with dynamic ones
	let allJoinTypeOptions = $derived(['InitialTaskWorker', ...availableWorkerClasses]);

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
		if (data.join_type !== joinType) {
			data.join_type = joinType;
			persistNodeDataDebounced();
		}
	});

	// Update code in the data object
	function handleCodeUpdate(newCode: string) {
		data.methods.consume_work_joined = newCode;
		persistNodeDataDebounced();
	}

	// Compute the title for the code section
	let consumeWorkJoinedTitle = $derived(
		`def consume_work_joined(self, tasks: list[${joinedInputType}]):`
	);

	async function handleCollapse() {
		await tick();
		updateNodeInternals(id);
	}

	function triggerOpenFullScreenEditor() {
		openFullScreenEditor(id, 'python');
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
	<div class="flex min-h-0 flex-grow flex-col px-1 pb-1">
		<EditableCodeSection
			title={consumeWorkJoinedTitle}
			code={data.methods.consume_work_joined}
			language="python"
			onUpdate={handleCodeUpdate}
			showReset={true}
			initialCollapsed={false}
			onUpdateSize={handleCollapse}
			onFullScreen={triggerOpenFullScreenEditor}
		/>
	</div>
</BaseWorkerNode>

<style>
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
