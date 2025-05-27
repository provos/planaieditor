<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte'; // Correct import
	import { useStore, useUpdateNodeInternals } from '@xyflow/svelte'; // Import useStore and useUpdateNodeInternals
	import type { Node, Edge } from '@xyflow/svelte';
	import { tick } from 'svelte';
	import { persistNodeDataDebounced } from '$lib/utils/nodeUtils';
	import { openFullScreenEditor } from '$lib/stores/fullScreenEditorStore.svelte'; // Import store function
	import { onMount } from 'svelte';

	export interface TaskWorkerData extends BaseWorkerData {
		consume_work: string;
	}

	const { id, data } = $props<{
		id: string;
		data: TaskWorkerData;
		isCached?: boolean;
	}>();

	const store = useStore(); // Access the store
	const updateNodeInternals = useUpdateNodeInternals(); // Initialize the hook

	// Use $state for the title and code content to ensure reactivity
	const defaultTitle = 'def consume_work(self, task):';
	let reactiveTitle = $state(defaultTitle);
	const consumeWorkCode = $derived(data.methods?.consume_work || '');
	const nodeVersion = $derived(data._lastUpdated || 0); // Key for re-rendering on external update

	onMount(() => {
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

	async function handleSizeChange() {
		await tick();
		updateNodeInternals(id);
	}

	function triggerOpenFullScreenEditor() {
		openFullScreenEditor(id, 'python');
	}
</script>

<BaseWorkerNode {id} {data} defaultName="TaskWorker">
	<div class="flex flex-col p-1">
		{#if data.methods?.consume_work}
			{#key nodeVersion}
				<EditableCodeSection
					title={reactiveTitle}
					code={consumeWorkCode}
					language="python"
					onUpdate={(newCode) => {
						data.methods.consume_work = newCode;
						persistNodeDataDebounced();
					}}
					showReset={true}
					onUpdateSize={handleSizeChange}
					onFullScreen={triggerOpenFullScreenEditor}
				/>
			{/key}
		{/if}
	</div>
</BaseWorkerNode>
