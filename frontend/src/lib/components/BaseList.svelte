<script lang="ts">
	import { getColorForType } from '$lib/utils/colorUtils';
	import Plus from 'phosphor-svelte/lib/Plus';
	import Trash from 'phosphor-svelte/lib/Trash';

	interface BaseListProps<T> {
		items: T[];
		onSelect: (item: T) => void;
		onDelete: (item: T) => void;
		canDelete: (item: T) => boolean;
		onCreate: () => void;
		emptyMessage: string;
		createButtonTitle: string;
		getName: (item: T) => string;
		getDescription?: (item: T) => string;
		getId: (item: T) => string;
		isSelected: (item: T) => boolean;
	}

	const {
		items,
		onSelect,
		onDelete,
		canDelete,
		onCreate,
		emptyMessage,
		createButtonTitle,
		getName,
		getDescription,
		getId,
		isSelected
	}: BaseListProps<any> = $props();
</script>

<div class="p-4">
	{#if items.length === 0}
		<p class="text-sm text-gray-500 italic">
			{emptyMessage}
		</p>
	{:else}
		<div class="space-y-2">
			{#each items as item (getId(item))}
				{@const color = getColorForType(getId(item))}
				{@const selected = isSelected(item)}
				<div
					class="group flex cursor-pointer items-center justify-between rounded p-2 shadow-sm transition-colors {selected
						? 'border-l-6 border-blue-600 bg-blue-100/70'
						: 'border-l-4 hover:bg-gray-100/50'}"
					style={selected ? '' : `border-left-color: ${color}; background-color: ${color}1A;`}
					data-testid="list-item"
					data-item-name={getName(item)}
					onclick={() => onSelect(item)}
					onkeydown={(event: KeyboardEvent) => {
						if (event.key === 'Enter' || event.key === ' ') {
							event.preventDefault(); // Prevent scrolling on spacebar
							onSelect(item);
						}
					}}
					role="button"
					tabindex="0"
				>
					<div class="flex-grow">
						<h3 class="text-sm font-semibold {selected ? 'text-blue-700' : 'text-gray-800'}">
							{getName(item)}
						</h3>
						{#if getDescription}
							<p class="text-xs {selected ? 'text-blue-600' : 'text-gray-600'}">
								{getDescription(item)}
							</p>
						{/if}
					</div>
					<button
						class="ml-2 flex h-6 w-6 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity group-hover:opacity-100 {selected
							? 'text-red-500 hover:bg-red-200'
							: 'hover:bg-red-100 hover:text-red-600'} {canDelete(item)
							? 'cursor-pointer'
							: 'cursor-not-allowed'} disabled:hover:text-gray-400"
						disabled={!canDelete(item)}
						aria-disabled={!canDelete(item)}
						title={!canDelete(item)
							? 'Cannot delete item with connected edges'
							: `Delete ${getName(item)}`}
						data-testid="delete-item-button"
						onclick={(event: MouseEvent) => {
							event.stopPropagation();
							onDelete(item);
						}}
					>
						<Trash size={14} weight="bold" />
					</button>
				</div>
			{/each}
		</div>
	{/if}

	<div class="mt-4 flex justify-center">
		<button
			class="z-10 flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-blue-500 shadow-sm hover:bg-blue-200"
			onclick={onCreate}
			title={createButtonTitle}
			data-testid="create-new-item-button"
		>
			<Plus size={16} weight="bold" />
		</button>
	</div>
</div>
