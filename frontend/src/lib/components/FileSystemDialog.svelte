<script lang="ts">
	import { Dialog, Button } from 'bits-ui';
	import File from 'phosphor-svelte/lib/File';
	import Folder from 'phosphor-svelte/lib/Folder';
	import ArrowUp from 'phosphor-svelte/lib/ArrowUp';
	import Spinner from 'phosphor-svelte/lib/Spinner';
	import { onMount } from 'svelte';
	import { listDirectory, type FilesystemItem as Item } from '$lib/utils/filesystemApi';

	// --- Props ---
	let {
		mode = 'open',
		title = mode === 'open' ? 'Open File' : 'Save File',
		initialPath = '/', // Default to root, backend should handle appropriately
		allowedExtensions = [],
		defaultFileName = '',
		onClose,
		onSave
	} = $props<{
		mode?: 'open' | 'save';
		title?: string;
		initialPath?: string;
		allowedExtensions?: string[];
		defaultFileName?: string;
		onClose: () => void;
		onSave: (path: string) => void;
	}>();

	// --- State ---
	let currentPath = $state(initialPath);
	let items = $state<Item[]>([]); // Use imported Item type
	let selectedItem = $state<Item | null>(null); // Use imported Item type
	let fileNameInput = $state(defaultFileName);
	let isLoading = $state(false);
	let error = $state<string | null>(null);

	// --- API Interaction ---
	async function fetchItems(path: string) {
		isLoading = true;
		error = null;
		selectedItem = null; // Reset selection when path changes
		if (
			mode !== 'save' &&
			(selectedItem === null || fileNameInput !== (selectedItem as Item).name)
		) {
			fileNameInput = '';
		}
		console.log(`Fetching items for path: ${path}`);

		try {
			const data = await listDirectory(path);

			currentPath = data.path;
			items = data.items
				.sort((a: Item, b: Item) => {
					if (a.type !== b.type) {
						return a.type === 'directory' ? -1 : 1;
					}
					return a.name.localeCompare(b.name);
				})
				.filter((item: Item) => {
					if (item.type === 'directory' || allowedExtensions.length === 0) {
						return true;
					}
					return allowedExtensions.some((ext: string) =>
						item.name.toLowerCase().endsWith(ext.toLowerCase())
					);
				});
		} catch (e: any) {
			console.error('Fetch items error:', e);
			error = e.message || 'An unknown error occurred while listing directory.';
			items = [];
		} finally {
			isLoading = false;
		}
	}

	// --- Effects ---
	// Fetch initial items when the component mounts
	onMount(() => {
		fetchItems(currentPath);
	});

	// --- Event Handlers ---
	function handleItemClick(item: Item) {
		if (item.type === 'directory') {
			fetchItems(item.path);
		} else {
			selectedItem = item;
			fileNameInput = item.name; // Pre-fill input with selected file name
		}
	}

	function handleUpDirectory() {
		const parentPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || '/';
		fetchItems(parentPath);
	}

	function handleSaveClick() {
		if (mode === 'open' && (!selectedItem || selectedItem.type !== 'file')) {
			error = 'Please select a file to open.';
			return;
		}
		if (mode === 'save' && !fileNameInput.trim()) {
			error = 'Please enter a filename.';
			return;
		}

		let finalPath: string;
		if (mode === 'save') {
			const sanitizedFileName = fileNameInput.trim().replace(/[\\/]/g, '');
			if (!sanitizedFileName) {
				error = 'Invalid filename.';
				return;
			}
			finalPath = currentPath.endsWith('/')
				? `${currentPath}${sanitizedFileName}`
				: `${currentPath}/${sanitizedFileName}`;
		} else if (selectedItem) {
			finalPath = selectedItem.path;
		} else {
			error = 'No file selected.';
			return;
		}

		console.log(`Saving/Opening path: ${finalPath}`);
		onSave(finalPath);
	}

	// --- Derived State ---
	const confirmButtonLabel = $derived(mode === 'open' ? 'Open' : 'Save');
	const isConfirmDisabled = $derived(
		isLoading ||
			(mode === 'open' && (!selectedItem || selectedItem.type !== 'file')) ||
			(mode === 'save' && !fileNameInput.trim())
	);
</script>

<!-- Using Dialog.Root without bind:open relies on conditional rendering by the parent -->
<Dialog.Root
	open={true}
	onOpenChange={(open) => {
		if (!open) {
			onClose();
		}
	}}
>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" />
		<Dialog.Content
			class="fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-[90vw] max-w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-md border bg-white p-6 shadow-lg focus:outline-none"
		>
			<Dialog.Title class="text-lg font-semibold leading-none tracking-tight">{title}</Dialog.Title>

			<div class="mt-4 flex items-center space-x-2 border-b pb-2">
				<Button.Root
					onclick={handleUpDirectory}
					disabled={isLoading || currentPath === '/'}
					title="Go to parent directory"
				>
					<ArrowUp class="h-5 w-5" />
				</Button.Root>
				<span class="text-muted-foreground flex-1 truncate text-sm" title={currentPath}
					>{currentPath}</span
				>
				{#if isLoading}
					<Spinner class="text-primary h-5 w-5 animate-spin" />
				{/if}
			</div>

			<div class="mt-4 h-[40vh] overflow-y-auto rounded-md border">
				{#if items.length === 0 && !isLoading && !error}
					<p class="text-muted-foreground p-4 text-center text-sm">Directory is empty.</p>
				{:else if error}
					<!-- Error handled below -->
				{:else}
					<ul class="divide-y">
						{#each items as item (item.path)}
							<li
								class="p-0 {selectedItem?.path === item.path
									? 'bg-accent bg-blue-200 font-medium'
									: ''}"
							>
								<button
									class="hover:bg-accent flex w-full cursor-pointer appearance-none items-center space-x-3 px-4 py-2 text-left text-sm"
									onclick={() => handleItemClick(item)}
									aria-selected={selectedItem?.path === item.path}
									role="treeitem"
									tabindex="0"
									onkeypress={(event) => {
										if (event.key === 'Enter' || event.key === ' ') {
											handleItemClick(item);
										}
									}}
									ondblclick={() => {
										if (item.type === 'directory') fetchItems(item.path);
										else if (mode === 'open') handleSaveClick();
									}}
								>
									{#if item.type === 'directory'}
										<Folder class="h-5 w-5 flex-shrink-0 text-blue-500" weight="fill" />
									{:else}
										<File class="text-muted-foreground h-5 w-5 flex-shrink-0" />
									{/if}
									<span class="flex-1 truncate" title={item.name}>{item.name}</span>
								</button>
							</li>
						{/each}
					</ul>
				{/if}
			</div>

			{#if error}
				<p class="text-destructive mt-2 text-sm">{error}</p>
			{/if}

			{#if mode === 'save'}
				<div class="mt-4">
					<label for="filename-input" class="text-foreground mb-1 block text-sm font-medium"
						>File name:</label
					>
					<input
						type="text"
						id="filename-input"
						bind:value={fileNameInput}
						class="bg-input focus:ring-ring w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2"
						placeholder="Enter file name"
						disabled={isLoading}
					/>
				</div>
			{/if}

			<div class="mt-6 flex justify-end space-x-2">
				<Dialog.Close>
					<Button.Root
						class="border-input bg-background ring-offset-background hover:bg-accent hover:text-accent-foreground focus-visible:ring-ring inline-flex h-10 items-center justify-center whitespace-nowrap rounded-md border px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
						disabled={isLoading}>Cancel</Button.Root
					>
				</Dialog.Close>
				<Button.Root onclick={handleSaveClick} disabled={isConfirmDisabled || isLoading}>
					{confirmButtonLabel}
				</Button.Root>
			</div>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
