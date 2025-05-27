<script lang="ts">
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import { onMount, untrack } from 'svelte';
	import { backendUrl } from '$lib/utils/backendUrl';
	import { formatErrorMessage, debounce } from '$lib/utils/utils';
	import { selectedInterpreterPath } from '$lib/stores/pythonInterpreterStore.svelte';
	import { toolNamesStore } from '$lib/stores/classNameStore.svelte';
	import Spinner from 'phosphor-svelte/lib/Spinner';
	import type { Tool } from '$lib/stores/toolStore.svelte';
	import { tools as toolsStore } from '$lib/stores/toolStore.svelte';

	const { id } = $props<{
		id: string;
	}>();

	const tool: Tool | undefined = $derived(toolsStore.find((t) => t.id === id));

	let currentName = $derived(tool?.name || '');
	let toolNameError = $state('');

	// Validation state
	let isValidatingTool = $state(false);
	let toolValidationError = $state<string | null>(null);
	let toolValidationWarnings = $state<string[]>([]);
	let isToolValid = $state<boolean | undefined>(undefined);

	onMount(() => {
		if (tool && tool.name && tool.code) {
			validateTool();
		}
	});

	function handleNameInput(event: Event) {
		currentName = (event.target as HTMLInputElement).value;
		toolNameError = '';
	}

	function finalizeNameChange() {
		if (!tool) return;
		const originalName = tool.name;
		const newName = currentName.trim();

		if (newName === originalName) {
			toolNameError = '';
			return;
		}
		if (newName === '') {
			toolNameError = 'Name cannot be empty.';
			currentName = originalName;
			return;
		}
		if (!/^[a-zA-Z0-9_-]*$/.test(newName)) {
			toolNameError = 'Invalid name. Use alphanumeric, _, -';
			currentName = originalName;
			return;
		}
		if (toolNamesStore.has(newName)) {
			toolNameError = 'Name already exists.';
			currentName = originalName;
			return;
		}
		toolNamesStore.delete(originalName);
		toolNamesStore.add(newName);
		tool.name = newName;
		toolNameError = '';
		debouncedValidateTool();
	}

	function handleCodeUpdate(newCode: string) {
		if (!tool) return;
		tool.code = newCode;
		debouncedValidateTool();
	}

	async function validateTool() {
		if (isValidatingTool || !tool || !tool.name || !tool.code) return;
		isValidatingTool = true;
		toolValidationError = null;
		toolValidationWarnings = [];
		isToolValid = undefined;
		try {
			const response = await fetch(`${backendUrl}/api/validate-tool`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ node: { data: { ...tool } } })
			});
			const result = await response.json();
			if (result.success) {
				isToolValid = true;
				toolValidationWarnings = result.warnings || [];
			} else {
				isToolValid = false;
				toolValidationError = result.error?.message || result.error || 'Unknown validation error';
			}
		} catch (error) {
			console.error('Error validating tool:', error);
			isToolValid = false;
			toolValidationError = 'Failed to connect to the server for tool validation.';
		} finally {
			isValidatingTool = false;
		}
	}

	const debouncedValidateTool = debounce(validateTool, 1200);

	$effect(() => {
		if (selectedInterpreterPath) {
			if (tool?.name && tool?.code) {
				untrack(validateTool);
			}
		}
	});
</script>

{#if tool}
	<div class="flex h-full flex-col bg-white">
		<div class="flex-none border-b bg-gray-50 p-1.5">
			<input
				type="text"
				value={currentName}
				oninput={handleNameInput}
				onblur={finalizeNameChange}
				onkeydown={(event) => {
					if (event.key === 'Enter' || event.key === 'Escape') {
						(event.target as HTMLInputElement).blur();
					}
				}}
				placeholder="Tool Name (e.g., my_tool_function)"
				class="nodrag w-full cursor-text rounded border px-1.5 py-1 text-sm font-medium focus:border-blue-400 focus:ring-1 {toolNameError
					? 'border-red-500 ring-red-500'
					: 'border-gray-200 focus:ring-blue-400'}"
				title="Enter the name of the tool function (alphanumeric, _, -)"
			/>
			{#if toolNameError}
				<div class="mt-0.5 text-xs text-red-500">{toolNameError}</div>
			{/if}
		</div>

		<div class="flex-none border-b bg-gray-50 p-1.5">
			<input
				type="text"
				bind:value={tool.description}
				placeholder="Tool description (optional, single line)"
				class="nodrag text-2xs w-full cursor-text rounded border border-gray-200 px-1.5 py-1 focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
				title="Enter a single-line description for the tool"
				onkeydown={(event) => {
					if (event.key === 'Enter' || event.key === 'Escape') {
						(event.target as HTMLInputElement).blur();
					}
				}}
			/>
		</div>

		<div class="relative min-h-0 flex-grow bg-white p-1.5">
			<EditableCodeSection
				title="Tool Function Code"
				code={tool.code}
				language="python"
				onUpdate={handleCodeUpdate}
				showReset={false}
				onUpdateSize={() => {}}
			/>
			<div class="absolute right-3 bottom-1 z-10">
				{#if isValidatingTool}
					<div class="rounded-sm bg-white/50 px-1.5 py-1.5">
						<Spinner size={12} class="animate-spin text-blue-500" weight="bold" />
					</div>
				{:else if tool?.name && tool?.code && isToolValid !== undefined}
					<p
						class="text-2xs {isToolValid
							? 'text-green-700'
							: 'text-red-700'} rounded-sm bg-white/50 px-1.5 py-1.5"
					>
						{isToolValid ? 'validated' : 'not validated'}
					</p>
				{/if}
			</div>
		</div>

		{#if !isValidatingTool && (toolValidationError || (isToolValid && toolValidationWarnings.length > 0))}
			<div class="flex-none">
				{#if toolValidationError && isToolValid === false}
					<div class="border-t border-red-200 bg-red-50 p-1.5">
						<p class="text-2xs font-semibold text-red-700">Error:</p>
						<p class="text-2xs text-red-600">{@html formatErrorMessage(toolValidationError)}</p>
					</div>
				{/if}
				{#if isToolValid && toolValidationWarnings.length > 0}
					<div class="border-t border-yellow-200 bg-yellow-50 p-1.5">
						<p class="text-2xs font-semibold text-yellow-700">Warnings:</p>
						<ul class="text-2xs mt-0.5 list-inside list-disc text-yellow-600">
							{#each toolValidationWarnings as warning}
								<li>{warning}</li>
							{/each}
						</ul>
					</div>
				{/if}
			</div>
		{/if}
	</div>
{:else}
	<div class="flex h-full items-center justify-center p-4">
		<p class="text-gray-500">Select a tool to configure it.</p>
	</div>
{/if}

<style>
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
