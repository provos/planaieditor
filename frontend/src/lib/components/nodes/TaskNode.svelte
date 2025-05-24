<script lang="ts">
	import Bookmark from './Bookmark.svelte';

	export interface TaskNodeData {
		nodeId: string; // Should be populated with the node's id
	}

	let { id, data } = $props<{
		id: string;
		data: TaskNodeData;
	}>();
</script>

<Bookmark
	{id}
	{data}
	type="task"
	title="Task Definitions"
	description="Click to open the task definitions pane where you can add, edit, and delete task classes."
/>
