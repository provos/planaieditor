<script lang="ts">
	import Bookmark from './Bookmark.svelte';

	let { id, data } = $props<{
		id: string;
		data: any;
	}>();
</script>

<Bookmark
	{id}
	{data}
	type="task"
	title="Task Definitions"
	description="Click to open the task definitions pane where you can add, edit, and delete task classes."
/>
