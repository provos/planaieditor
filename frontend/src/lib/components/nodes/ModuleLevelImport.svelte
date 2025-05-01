<script lang="ts">
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import { NodeResizer } from '@xyflow/svelte';
	import HeaderIcon from '$lib/components/HeaderIcon.svelte';
	import { backendUrl } from '$lib/utils/backendUrl';
	import { debounce, formatErrorMessage } from '$lib/utils/utils';
	import Spinner from 'phosphor-svelte/lib/Spinner';
	import { onMount } from 'svelte';
	import { selectedInterpreterPath } from '$lib/stores/pythonInterpreterStore.svelte';

	export interface ModuleLevelImportData {
		code: string;
		nodeId: string;
	}

	let { id, data } = $props<{
		id: string;
		data: ModuleLevelImportData;
	}>();

	let isLoading = $state<boolean>(false);
	let errorMessage = $state<string | null>(null);
	let isValid = $state<boolean | null>(null); // null = unchecked, true = valid, false = invalid

	async function validateImportCode() {
		if (!data.code.trim()) {
			isValid = true; // Empty code is valid
			errorMessage = null;
			isLoading = false;
			return;
		}

		if (isLoading) {
			// Allow one validation at a time
			return;
		}

		isLoading = true;
		errorMessage = null;
		isValid = null; // Reset validity while loading

		try {
			const response = await fetch(`${backendUrl}/api/validate-module-imports`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ import_code: data.code })
			});
			const result = await response.json();
			isValid = result.success;
			errorMessage = result.success ? null : result.error;
		} catch (error) {
			console.error('Error validating import code:', error);
			errorMessage = 'Failed to connect to the validation server.';
			isValid = false;
		} finally {
			isLoading = false;
		}
	}

	const debouncedValidate = debounce(validateImportCode, 1000);

	let handleCodeUpdate = (code: string) => {
		data.code = code;
		isValid = null; // Mark as unchecked when code changes
		errorMessage = null;
		isLoading = true; // Show loading indicator immediately for responsiveness
		debouncedValidate();
	};

	onMount(() => {
		validateImportCode(); // Validate initial code on mount
	});

	// Validate the code when the interpreter path changes
	$effect(() => {
		if (selectedInterpreterPath.value) {
			validateImportCode();
		}
	});
</script>

<div
	class="modulelevelimport-node flex h-full flex-col overflow-auto rounded-md border border-gray-300 bg-white shadow-md"
>
	<!-- Node Resizer -->
	<NodeResizer
		minWidth={200}
		minHeight={150}
		handleClass="resize-handle-modulelevelimport"
		lineClass="resize-line-modulelevelimport"
	/>

	<!-- Header with Task Type Selector -->
	<div class="flex-none border-b bg-emerald-100 p-1">
		<HeaderIcon workerType={'modulelevelimport'} />
		<div
			class="w-full cursor-pointer rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-gray-100"
		>
			Module Level Import
		</div>
	</div>

	<!-- JSON Data Editor -->
	<div class="relative flex h-full min-h-0 flex-col p-1.5">
		<EditableCodeSection
			title="Module Level Import"
			code={data.code}
			language="python"
			onUpdate={handleCodeUpdate}
		/>
		<!-- Validation Status -->
		<div class="absolute bottom-1 right-3 z-10">
			{#if isLoading}
				<div class="rounded-sm bg-white/50 px-1.5 py-1.5">
					<Spinner size={12} class="animate-spin text-blue-500" />
				</div>
			{:else if isValid !== null}
				<p
					class="text-2xs {isValid
						? 'text-green-700'
						: 'text-red-700'} rounded-sm bg-white/50 px-1.5 py-1.5"
					title={isValid ? 'Imports are valid' : 'Imports are invalid'}
				>
					{isValid ? 'validated' : 'invalid'}
				</p>
			{/if}
		</div>
	</div>

	<!-- Error Display Area -->
	{#if errorMessage}
		<div class="mt-auto flex-none border-t border-red-200 bg-red-50 p-1.5">
			<p class="text-2xs font-semibold text-red-700">Error:</p>
			<p class="text-2xs text-red-600">{@html formatErrorMessage(errorMessage)}</p>
		</div>
	{/if}
</div>

<style>
	/* Use global styles defined elsewhere for handles/resizers if consistent */
	:global(.resize-handle-modulelevelimport) {
		width: 12px !important;
		height: 12px !important;
		border-radius: 3px !important;
		border: 2px solid var(--color-emerald-200) !important;
		background-color: rgba(100, 149, 237, 0.2) !important;
	}

	:global(.resize-line-modulelevelimport) {
		border-color: var(--color-emerald-200) !important;
		border-width: 2px !important;
	}

	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
