<script lang="ts">
	import type { Component } from 'svelte';

	export interface ContextMenuItem {
		label: string;
		iconComponent?: Component;
		action: () => void;
		danger?: boolean;
	}

	// Props
	const { items, x, y, onClose } = $props<{
		items: ContextMenuItem[];
		x: number;
		y: number;
		onClose: () => void;
	}>();

	// Handle item click
	function handleItemClick(item: ContextMenuItem) {
		item.action();
		onClose();
	}

	// Handle clicks outside the menu
	function handleOutsideClick(event: MouseEvent) {
		const target = event.target as HTMLElement;
		const menu = document.getElementById('context-menu');

		if (menu && !menu.contains(target)) {
			onClose();
		}
	}

	// Setup click listener when the menu appears
	$effect(() => {
		document.addEventListener('mousedown', handleOutsideClick);
		return () => {
			document.removeEventListener('mousedown', handleOutsideClick);
		};
	});
</script>

<div
	id="context-menu"
	class="absolute z-50 min-w-40 overflow-hidden rounded-md border border-gray-200 bg-white shadow-lg"
	style="left: {x}px; top: {y}px;"
>
	<div class="py-1">
		{#each items as item (item.label)}
			<button
				class="flex w-full items-center px-4 py-2 text-left text-sm hover:bg-gray-100 {item.danger
					? 'text-red-600 hover:text-red-700'
					: 'text-gray-700'}"
				onclick={() => handleItemClick(item)}
			>
				{#if item.iconComponent}
					<item.iconComponent class="mr-2 h-4 w-4" />
				{/if}
				{item.label}
			</button>
		{/each}
	</div>
</div>
