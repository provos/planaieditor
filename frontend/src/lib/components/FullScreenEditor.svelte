<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { useStore } from '@xyflow/svelte';
	import type { Node } from '@xyflow/svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import FloppyDisk from 'phosphor-svelte/lib/FloppyDisk';
	import X from 'phosphor-svelte/lib/X';
	import {
		fullScreenEditorState,
		saveFullScreenEditor,
		closeFullScreenEditorStore
	} from '$lib/stores/fullScreenEditorStore.svelte';
	import { backendUrl } from '$lib/utils/backendUrl';

	let isLoading = $state(true);
	let currentCode = $state<string | undefined>(undefined);
	let editorContainerRef: HTMLDivElement | undefined = $state();

	const { nodes } = useStore();

	async function handleLoad() {
		isLoading = true;

		// Get the node with the id from the store
		let currentNode: Node | undefined = undefined;
		nodes.subscribe((nodes) => {
			currentNode = nodes.find((node) => node.id === fullScreenEditorState.id);
		})();
		if (!currentNode) {
			console.error('Node not found');
			return;
		}
		const response = await fetch(`${backendUrl}/api/get-node-code`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(currentNode)
		});
		const data = await response.json();
		currentCode = data.code;

		isLoading = false;
		await tick();
	}

	onMount(async () => {
		console.log('FullScreenEditor mounted');
		await handleLoad();
	});

	function internalSave() {
		saveFullScreenEditor(currentCode);
	}

	function internalClose() {
		closeFullScreenEditorStore();
	}

	function handleCodeUpdate(newCode: string) {
		currentCode = newCode;
	}
</script>

<div
	class="fixed inset-0 z-50 flex flex-col bg-gray-800/75 p-4 backdrop-blur-sm"
	bind:this={editorContainerRef}
>
	{#if isLoading}
		<div class="flex h-full flex-grow items-center justify-center">
			<p class="text-2xl text-white">Loading editor...</p>
		</div>
	{:else}
		<div class="mb-2 flex items-center justify-between rounded-t-md bg-gray-700 p-2">
			<h2 class="text-lg font-semibold text-white">Edit Code</h2>
			<div class="flex space-x-2">
				<button
					onclick={internalSave}
					class="flex items-center rounded bg-blue-500 px-3 py-1.5 text-sm text-white hover:bg-blue-600"
					title="Save changes"
				>
					<FloppyDisk size={18} class="mr-1.5" />
					Save
				</button>
				<button
					onclick={internalClose}
					class="flex items-center rounded bg-gray-600 px-3 py-1.5 text-sm text-white hover:bg-gray-500"
					title="Close editor"
				>
					<X size={18} class="mr-1.5" />
					Cancel
				</button>
			</div>
		</div>
		<div class="flex-grow overflow-hidden rounded-b-md bg-white">
			{#if editorContainerRef && !isLoading}
				<EditableCodeSection
					title="Full Screen Edit"
					code={currentCode}
					language={fullScreenEditorState.language}
					onUpdate={handleCodeUpdate}
					onUpdateSize={() => {}}
					maxHeight={editorContainerRef?.clientHeight ? editorContainerRef.clientHeight - 80 : 600}
				/>
			{/if}
		</div>
	{/if}
</div>

<style>
	/* Ensure the editor within this component takes full available height */
	:global(.monaco-editor) {
		height: 100% !important;
		width: 100% !important;
	}
	.flex-grow > div {
		/* This targets the div wrapping EditableCodeSection */
		height: 100%;
	}
</style>
