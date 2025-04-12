<script lang="ts">
	// Simple drag handle component to be placed at the top of nodes
</script>

<div class="node-drag-handle custom-drag-handle" aria-label="Drag to move node">
	<div class="handle-dots">
		<span></span>
		<span></span>
		<span></span>
	</div>
</div>

<style>
	.node-drag-handle {
		width: 100%;
		height: 8px;
		background-color: #f3f4f6;
		cursor: move;
		border-radius: 4px 4px 0 0;
		display: flex;
		justify-content: center;
		align-items: center;
	}

	.handle-dots {
		display: flex;
		gap: 3px;
	}

	.handle-dots span {
		width: 4px;
		height: 4px;
		background-color: #9ca3af;
		border-radius: 50%;
	}

	.node-drag-handle:hover {
		background-color: #e5e7eb;
	}

	.node-drag-handle:hover .handle-dots span {
		background-color: #6b7280;
	}
</style>
