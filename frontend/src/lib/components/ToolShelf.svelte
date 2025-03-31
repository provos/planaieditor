<script lang="ts">
	// Handles the start of dragging a new node
	function onDragStart(event: DragEvent, nodeType: string) {
		if (event.dataTransfer) {
			event.dataTransfer.setData('application/reactflow', nodeType);
			event.dataTransfer.effectAllowed = 'move';
		}
	}
</script>

<div class="flex gap-4">
	<div class="text-lg font-bold">Tools:</div>

	<div
		class="cursor-grab rounded-md border border-gray-300 bg-white p-2 shadow-md transition-shadow hover:shadow-lg"
		draggable="true"
		on:dragstart={(e) => onDragStart(e, 'task')}
	>
		<div class="text-sm font-semibold">Task</div>
		<div class="text-xs text-gray-500">Data Model</div>
	</div>

	<!-- More node types can be added here later -->
</div>
