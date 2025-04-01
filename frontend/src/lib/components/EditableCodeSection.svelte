<script lang="ts">
	import CodeMirror from 'svelte-codemirror-editor';
	import { python } from '@codemirror/lang-python';
	import { markdown } from '@codemirror/lang-markdown';
	import ChevronDown from 'phosphor-svelte/lib/ArrowDown';
	import ChevronRight from 'phosphor-svelte/lib/ArrowRight';
	import type { LanguageSupport } from '@codemirror/language';

	let {
		title,
		code,
		language = 'python',
		initialCollapsed = false,
		onUpdate
	} = $props<{
		title: string;
		code: string;
		language?: 'python' | 'markdown';
		initialCollapsed?: boolean;
		onUpdate: (newCode: string) => void;
	}>();

	let collapsed = $state(initialCollapsed);

	const langExtension: LanguageSupport = language === 'python' ? python() : markdown();

	function toggleCollapse() {
		collapsed = !collapsed;
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
			fontFamily: 'monospace'
		},
		'.cm-scroller': {
			overflow: 'auto'
		},
		'.cm-editor': {
			height: '100%'
		}
	};
</script>

<div class="flex h-full min-h-0 flex-col">
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div
		class="mb-1 flex flex-none cursor-pointer items-center"
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
