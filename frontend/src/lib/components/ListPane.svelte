<script lang="ts">
	import { splitPaneConfig } from '$lib/stores/splitPaneStore.svelte';
	import ToolList from './ToolList.svelte';
	import { Tabs } from 'bits-ui';
	import { nodes as graphNodesStore } from '$lib/stores/graphStore'; // Svelte 5 store for nodes
	import { get } from 'svelte/store';
	import type { Node } from '@xyflow/svelte';

	// Determine active tab based on selectedNodeId
	let activeTab = $derived(getActiveTab());

	function getActiveTab(): 'tasks' | 'tools' {
		const selectedNodeId = splitPaneConfig.selectedNodeId;
		if (selectedNodeId) {
			const currentGraphNodes: Node[] = get(graphNodesStore); // Get the actual array
			const selectedNode = currentGraphNodes.find((node) => node.id === selectedNodeId);
			if (selectedNode && selectedNode.type === 'tool') {
				return 'tools';
			}
		}
		return 'tasks'; // Default tab
	}

	function handleTabChange(value: string | undefined) {
		if (value === 'tasks') {
			// If user explicitly clicks "Task Definitions", clear selected node ID if it was a tool
			const selectedNodeId = splitPaneConfig.selectedNodeId;
			if (selectedNodeId) {
				const currentGraphNodes: Node[] = get(graphNodesStore);
				const selectedNode = currentGraphNodes.find((node) => node.id === selectedNodeId);
				if (selectedNode && selectedNode.type === 'tool') {
					splitPaneConfig.selectedNodeId = null;
				}
			}
		}
		// activeTab will update reactively via $derived(getActiveTab())
	}
</script>

<div class="h-full overflow-auto border border-gray-300 bg-gray-200">
	<Tabs.Root value={activeTab} onValueChange={handleTabChange} class="flex h-full flex-col p-2">
		<Tabs.List class="mb-1 flex rounded-md bg-gray-200/70 p-0">
			<Tabs.Trigger
				value="tasks"
				class="flex-1 rounded-md px-3 py-1.5 text-center text-sm font-medium transition-colors duration-150 hover:bg-gray-300/50 data-[state=active]:bg-white data-[state=active]:shadow-sm"
			>
				Task Definitions
			</Tabs.Trigger>
			<Tabs.Trigger
				value="tools"
				class="flex-1 rounded-md px-3 py-1.5 text-center text-sm font-medium transition-colors duration-150 hover:bg-gray-300/50 data-[state=active]:bg-white data-[state=active]:shadow-sm"
			>
				Tool Definitions
			</Tabs.Trigger>
		</Tabs.List>

		<Tabs.Content value="tasks" class="flex-grow rounded-md bg-white p-3 shadow-inner">
			<p class="text-sm text-gray-600">Task Definitions Placeholder</p>
			<!-- Future: Component for task definitions will go here -->
		</Tabs.Content>

		<Tabs.Content value="tools" class="flex-grow overflow-auto rounded-md bg-white shadow-inner">
			<ToolList />
		</Tabs.Content>
	</Tabs.Root>
</div>
