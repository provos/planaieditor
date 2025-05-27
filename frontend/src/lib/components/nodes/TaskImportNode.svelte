<script lang="ts">
	import Bookmark from './Bookmark.svelte';

	export interface TaskImportNodeData {
		nodeId: string; // Should be populated with the node's id
	}

	const { id, data } = $props<{
		id: string;
		data: TaskImportNodeData;
	}>();
</script>

<Bookmark
	{id}
	{data}
	type="taskimport"
	title="Task Imports"
	description="Click to open the task imports pane where you can add, edit, and manage imported task classes from external modules."
/>
