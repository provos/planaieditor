<script lang="ts">
	import CodeMirror from 'svelte-codemirror-editor';
	import { python } from '@codemirror/lang-python';
	import { markdown } from '@codemirror/lang-markdown';
	import ChevronDown from 'phosphor-svelte/lib/ArrowDown';
	import ChevronRight from 'phosphor-svelte/lib/ArrowRight';
	import Trash from 'phosphor-svelte/lib/Trash';
	import type { LanguageSupport } from '@codemirror/language';

	let {
		title = '',
		code,
		language = 'python',
		initialCollapsed = false,
		onUpdate,
		onReset = undefined,
		showReset = false,
		onCollapseToggle
	} = $props<{
		title?: string;
		code: string;
		language?: 'python' | 'markdown';
		initialCollapsed?: boolean;
		onUpdate: (newCode: string) => void;
		onReset?: () => void;
		showReset?: boolean;
		onCollapseToggle?: () => void;
	}>();

	let collapsed = $state(initialCollapsed);

	const langExtension: LanguageSupport = language === 'python' ? python() : markdown();

	function toggleCollapse() {
		collapsed = !collapsed;
		onCollapseToggle?.();
	}

	function handleCodeUpdate(event: CustomEvent) {
		onUpdate(event.detail);
	}

	const editorStyles = {
		'&': {
			border: '1px solid #e2e8f0',
			borderRadius: '0.25rem',
			fontSize: '0.7rem',
			height: '100%', // Fill container height
			width: '100%',
			overflow: 'hidden',
			display: 'flex',
			flexDirection: 'column',
			minHeight: '3rem' // Ensure at least 3 lines height
		},
		'.cm-content': {
			fontFamily: 'monospace',
			cursor: 'text' // Ensure text cursor in editor content
		},
		'.cm-scroller': {
			overflow: 'auto'
		},
		'.cm-editor': {
			height: '100%',
			cursor: 'text' // Ensure text cursor in editor
		}
	};
</script>

<div class="flex h-full min-h-0 flex-col">
	<!-- Title section with possible reset button -->
	<div class="mb-1 flex flex-none items-center justify-between">
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div
			class="flex cursor-pointer items-center"
			onclick={toggleCollapse}
			role="button"
			tabindex="0"
		>
			{#if collapsed}
				<ChevronRight size={12} class="mr-1 text-gray-500" />
			{:else}
				<ChevronDown size={12} class="mr-1 text-gray-500" />
			{/if}
			<h3 class="text-2xs font-semibold text-gray-600">{title}</h3>
		</div>

		{#if showReset && onReset}
			<button
				class="text-2xs flex items-center rounded border border-gray-200 bg-gray-50 px-1 py-0.5 text-gray-500 opacity-70 hover:bg-gray-100 hover:text-red-500 hover:opacity-100"
				onclick={onReset}
			>
				<Trash size={10} weight="bold" class="mr-1" />
				Reset
			</button>
		{/if}
	</div>

	{#if !collapsed}
		<div class="min-h-0 flex-grow overflow-hidden">
			<CodeMirror
				value={code}
				lang={langExtension}
				styles={editorStyles}
				on:change={handleCodeUpdate}
				basic={true}
			/>
		</div>
	{/if}
</div>

<style>
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
