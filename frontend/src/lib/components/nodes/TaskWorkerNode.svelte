<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte'; // Correct import
	import { useStore, useUpdateNodeInternals } from '@xyflow/svelte'; // Import useStore and useUpdateNodeInternals
	import type { Node, Edge } from '@xyflow/svelte';
	import { tick } from 'svelte';
	export interface TaskWorkerData extends BaseWorkerData {
		consumeWork: string;
	}

	let { id, data } = $props<{
		id: string;
		data: TaskWorkerData;
	}>();

	const store = useStore(); // Access the store
	const updateNodeInternals = useUpdateNodeInternals(); // Initialize the hook

	// Use $state for the title and code content to ensure reactivity
	const defaultTitle = 'def consume_work(self, task):';
	let reactiveTitle = $state(defaultTitle);

	// Default code for consume_work
	const defaultConsumeWork = `    # Process the input task and produce output
    # self.publish_work(output_task, input_task=task)
    pass`;

	// Initialize if not already set
	if (!data.consumeWork) {
		data.consumeWork = defaultConsumeWork;
	}

	$effect(() => {
		let currentNodes: Node[] = [];
		let currentEdges: Edge[] = [];

		// Subscribe to nodes store changes
		const unsubNodes = store.nodes.subscribe((nodesValue) => {
			currentNodes = nodesValue || [];
			updateTitleBasedOnInputs(currentNodes, currentEdges);
		});

		// Subscribe to edges store changes
		const unsubEdges = store.edges.subscribe((edgesValue) => {
			currentEdges = edgesValue || [];
			updateTitleBasedOnInputs(currentNodes, currentEdges);
		});

		// Initial update
		updateTitleBasedOnInputs(currentNodes, currentEdges);

		// Cleanup
		return () => {
			unsubNodes();
			unsubEdges();
		};
	});

	// Helper function to calculate inputs and update title
	function updateTitleBasedOnInputs(nodes: Node[], edges: Edge[]) {
		if (!edges || !nodes) {
			reactiveTitle = defaultTitle;
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
				return sourceNode?.data?.className;
			})
			.filter(Boolean) as string[];

		// Update the title based on the *first* calculated input type
		reactiveTitle = sourceClassNames[0]
			? `def consume_work(self, task: ${sourceClassNames[0]}):`
			: defaultTitle;
	}

	async function handleCollapse() {
		await tick();
		updateNodeInternals(id);
	}
</script>

<BaseWorkerNode {id} {data} defaultName="TaskWorker">
	<div class="flex min-h-0 flex-grow flex-col overflow-hidden p-1">
		{#if data.methods?.consume_work}
			<EditableCodeSection
				title={reactiveTitle}
				code={data.methods.consume_work}
				language="python"
				onUpdate={(newCode) => (data.methods.consume_work = newCode)}
				showReset={true}
				onCollapseToggle={handleCollapse}
			/>
		{/if}
	</div>
</BaseWorkerNode>
