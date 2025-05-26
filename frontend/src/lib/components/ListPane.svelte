<script lang="ts">
	import { splitPaneConfig } from '$lib/stores/splitPaneStore.svelte';
	import ToolList from './ToolList.svelte';
	import TaskList from './TaskList.svelte';
	import TaskImportList from './TaskImportList.svelte';
	import { Tabs } from 'bits-ui';
	import { nodes as graphNodesStore } from '$lib/stores/graphStore'; // Svelte 5 store for nodes
	import { get } from 'svelte/store';
	import type { Node } from '@xyflow/svelte';

	// Determine active tab based on selectedNodeId
	let activeTab = $state('tasks');

	$effect(() => {
		const selectedNodeId = splitPaneConfig.selectedNodeId;
		if (selectedNodeId) {
			const currentGraphNodes: Node[] = get(graphNodesStore); // Get the actual array
			const selectedNode = currentGraphNodes.find((node) => node.id === selectedNodeId);
			if (!selectedNode) return;

			let newActiveTab = 'tasks';
			switch (selectedNode.type) {
				case 'tool':
					newActiveTab = 'tools';
					break;
				case 'task':
					newActiveTab = 'tasks';
					break;
				case 'taskimport':
					newActiveTab = 'taskimports';
					break;
			}
			activeTab = newActiveTab;
		}
	});

	function handleTabChange(value: string | undefined) {
		if (
			(value === 'tasks' && splitPaneConfig.upperNodeType !== 'task') ||
			(value === 'taskimports' && splitPaneConfig.upperNodeType !== 'taskimport') ||
			(value === 'tools' && splitPaneConfig.upperNodeType !== 'tool')
		) {
			splitPaneConfig.upperNodeId = null;
			splitPaneConfig.upperNodeType = null;
		}
	}
</script>

<div class="h-full overflow-auto border border-gray-300 bg-gray-200">
	<Tabs.Root value={activeTab} onValueChange={handleTabChange} class="flex h-full flex-col p-2">
		<Tabs.List class="mb-1 flex shrink-0 rounded-md bg-gray-200/70 p-0">
			<Tabs.Trigger
				value="tasks"
				data-testid="tasks-tab"
				class="flex-1 rounded-md px-3 py-1.5 text-center text-sm font-medium transition-colors duration-150 hover:bg-gray-300/50 data-[state=active]:bg-white data-[state=active]:shadow-sm"
			>
				Task Definitions
			</Tabs.Trigger>
			<Tabs.Trigger
				value="taskimports"
				class="flex-1 rounded-md px-3 py-1.5 text-center text-sm font-medium transition-colors duration-150 hover:bg-gray-300/50 data-[state=active]:bg-white data-[state=active]:shadow-sm"
			>
				Task Imports
			</Tabs.Trigger>
			<Tabs.Trigger
				value="tools"
				class="flex-1 rounded-md px-3 py-1.5 text-center text-sm font-medium transition-colors duration-150 hover:bg-gray-300/50 data-[state=active]:bg-white data-[state=active]:shadow-sm"
			>
				Tool Definitions
			</Tabs.Trigger>
		</Tabs.List>

		<Tabs.Content
			value="tasks"
			data-testid="tasks-tab-content"
			class="min-h-0 flex-1 overflow-hidden rounded-md bg-white shadow-inner"
		>
			<div class="h-full overflow-auto p-3">
				<TaskList />
			</div>
		</Tabs.Content>

		<Tabs.Content
			value="taskimports"
			class="min-h-0 flex-1 overflow-hidden rounded-md bg-white shadow-inner"
		>
			<div class="h-full overflow-auto p-3">
				<TaskImportList />
			</div>
		</Tabs.Content>

		<Tabs.Content
			value="tools"
			class="min-h-0 flex-1 overflow-hidden rounded-md bg-white shadow-inner"
		>
			<div class="h-full overflow-auto p-3">
				<ToolList />
			</div>
		</Tabs.Content>
	</Tabs.Root>
</div>
