<script lang="ts">
	import Bookmark from './Bookmark.svelte';

	const { id, data } = $props<{
		id: string;
		data: any;
	}>();
</script>

<Bookmark
	{id}
	{data}
	type="tool"
	title="Tool Library"
	description="Click on this node to open the tool library where you can add, edit, and delete tools."
/>
