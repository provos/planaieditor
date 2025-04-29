<script lang="ts">
	import { Dialog } from 'bits-ui';

	let {
		open = false,
		onSave = (name: string) => {},
		onClose = () => {},
		initialName = ''
	}: {
		open: boolean;
		onSave: (name: string) => void;
		onClose: () => void;
		initialName: string;
	} = $props();

	let name = $state(initialName);

	$effect(() => {
		name = initialName;
	});

	function handleSubmit() {
		if (name.trim()) {
			onSave(name.trim());
			onClose();
		}
	}

	function handleClose() {
		onClose();
	}
</script>

<Dialog.Root {open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 bg-black/50 backdrop-blur-sm" />
		<Dialog.Content
			class="fixed left-1/2 top-1/2 w-[400px] -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-lg"
		>
			<Dialog.Title class="mb-4 text-lg font-semibold text-gray-900">Enter Graph Name</Dialog.Title>
			<Dialog.Description class="mb-4 text-sm text-gray-600">
				Please provide a name for your graph. This will be used when saving or exporting.
			</Dialog.Description>
			<form onsubmit={handleSubmit} class="space-y-4">
				<input
					type="text"
					bind:value={name}
					placeholder="Enter graph name"
					class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
				/>
				<div class="flex justify-end gap-2">
					<button
						type="button"
						class="rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
						onclick={handleClose}
					>
						Cancel
					</button>
					<button
						type="submit"
						class="rounded-md bg-blue-500 px-3 py-2 text-sm font-medium text-white hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
						disabled={!name.trim()}
					>
						Save
					</button>
				</div>
			</form>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
