<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import ChevronDown from 'phosphor-svelte/lib/ArrowDown';
	import ChevronRight from 'phosphor-svelte/lib/ArrowRight';
	import Trash from 'phosphor-svelte/lib/Trash';
	import ArrowsOutSimple from 'phosphor-svelte/lib/ArrowsOutSimple';
	import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';
	import { tick } from 'svelte';
	import { monacoInstance } from '$lib/stores/monacoStore.svelte'; // Import the shared instance

	const {
		title = '',
		code,
		language = 'python',
		initialCollapsed = false,
		onUpdate,
		onReset = undefined,
		showReset = false,
		onUpdateSize,
		onFullScreen,
		fontsize = 11,
		maxHeight = 400,
		additionalStyle = 'min-w-[60ch]'
	} = $props<{
		title?: string;
		code: string;
		language?: 'python' | 'markdown' | 'json' | 'javascript' | 'typescript';
		initialCollapsed?: boolean;
		onUpdate: (newCode: string) => void;
		onReset?: () => void;
		showReset?: boolean;
		onUpdateSize?: () => void;
		onFullScreen?: () => void;
		fontsize?: number;
		maxHeight?: number; // Maximum height before scrolling
		additionalStyle?: string;
	}>();

	let collapsed = $state(initialCollapsed);
	let editorContainer: HTMLDivElement | undefined = $state();
	let editor: Monaco.editor.IStandaloneCodeEditor | undefined;
	let contentHeight = $state(0); // Track content height
	let currentCode = $state(code);
	let resizeObserver: ResizeObserver | undefined;

	onDestroy(async () => {
		// Dispose editor and models
		editor?.dispose();

		resizeObserver?.disconnect(); // Disconnect observer on destroy

		// Clear other references
		editor = undefined;
		editorContainer = undefined;
	});

	// Effect to create the editor once the monaco instance and container are ready
	$effect(() => {
		if (monacoInstance.instance && editorContainer && !editor) {
			editor = monacoInstance.instance.editor.create(editorContainer!, {
				value: code,
				language: language,
				automaticLayout: false,
				fontSize: fontsize,
				minimap: { enabled: false },
				scrollBeyondLastLine: false,
				scrollbar: {
					vertical: 'auto',
					horizontalScrollbarSize: 8,
					verticalScrollbarSize: 8,
					handleMouseWheel: false // Initially disable mouse wheel handling
				},
				theme: 'vs-light',
				fixedOverflowWidgets: true // Allow tooltips to escape container bounds
			});

			// Listen for content changes *after* editor is created
			editor.onDidChangeModelContent(() => {
				currentCode = editor?.getValue() ?? '';
				onUpdate(currentCode);
				updateEditorHeight();
			});

			// Set up content height tracking
			editor.onDidContentSizeChange((e) => {
				contentHeight = e.contentHeight;
				updateEditorHeight();
			});

			// Handle focus and blur to toggle mouse wheel scrolling
			editor.onDidFocusEditorWidget(() => {
				editor?.updateOptions({ scrollbar: { handleMouseWheel: true } });
			});

			editor.onDidBlurEditorWidget(() => {
				editor?.updateOptions({ scrollbar: { handleMouseWheel: false } });
			});

			// Initial layout and height calculation
			tick().then(() =>
				requestAnimationFrame(() => {
					if (editor && editorContainer) {
						editor.layout();
						updateEditorHeight();
					} else {
						console.warn('Editor or container not available during initial layout attempt.');
					}
				})
			);
		}
	});

	// Function to update editor height based on content
	function updateEditorHeight() {
		if (!editor || !editorContainer) return;

		// Get current content height
		const height = editor.getContentHeight();

		// Apply height with a maximum limit
		const newHeight = Math.min(height, maxHeight);
		editorContainer.style.height = `${newHeight}px`;

		// Update the editor layout with the new dimensions
		const width = editorContainer.clientWidth;
		editor.layout({ width, height: newHeight });

		// Show/hide scrollbar based on content height versus container height
		if (height > maxHeight) {
			// Content exceeds max height, enable scrollbar
			editor.updateOptions({ scrollbar: { vertical: 'visible' } });
		} else {
			// Content fits, hide scrollbar
			editor.updateOptions({ scrollbar: { vertical: 'hidden' } });
		}
		onUpdateSize?.();
	}

	function toggleCollapse() {
		collapsed = !collapsed;
		onUpdateSize?.();
		if (!collapsed && editor) {
			console.log('Editor container should now be visible. Scheduling layout.');

			// Wait for Svelte to update the DOM
			tick().then(() => {
				// Then, wait for the browser's next rendering frame
				// to ensure the container has its dimensions calculated.
				requestAnimationFrame(() => {
					if (editor && editorContainer && editorContainer.offsetParent !== null) {
						// Check if the container is actually visible and has dimensions
						const { width, height } = editorContainer.getBoundingClientRect();
						if (width > 0 && height > 0) {
							console.log(`Layouting editor in container: ${width}x${height}`);
							editor.layout();
							updateEditorHeight(); // Update height when becoming visible
						} else {
							console.warn('Editor container has zero dimensions when attempting layout.');
						}
					} else {
						console.warn('Editor or editor container not ready or not visible for layout.');
					}
				});
			});
		}
	}

	onMount(() => {
		if (!editorContainer) return;

		resizeObserver = new ResizeObserver(() => {
			// When the container div resizes, tell the editor to re-layout.
			// RAF ensures we run after the browser has painted the resize.
			requestAnimationFrame(() => {
				editor?.layout();
			});
		});

		resizeObserver.observe(editorContainer);

		// Cleanup function is implicitly returned by onMount
		return () => {
			resizeObserver?.disconnect();
		};
	});
</script>

<div class="flex min-h-0 flex-col">
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

		<div class="flex items-center space-x-1">
			{#if showReset && onReset}
				<button
					class="text-2xs flex items-center rounded border border-gray-200 bg-gray-50 px-1 py-0.5 text-gray-500 opacity-70 hover:bg-gray-100 hover:text-red-500 hover:opacity-100"
					onclick={onReset}
					title="Remove the optional function"
				>
					<Trash size={10} weight="bold" class="mr-1" />
					Reset
				</button>
			{/if}
			{#if onFullScreen}
				<button
					class="text-2xs flex items-center rounded border border-gray-200 bg-gray-50 px-1 py-0.5 text-gray-500 opacity-70 hover:bg-gray-100 hover:text-blue-500 hover:opacity-100"
					onclick={onFullScreen}
					title="Fullscreen"
				>
					<ArrowsOutSimple size={10} weight="bold" class="mr-1" />
				</button>
			{/if}
		</div>
	</div>

	<div
		class="{collapsed
			? 'hidden h-0'
			: 'flex-grow'} transition-height p-1 duration-200 {additionalStyle}"
	>
		<div
			bind:this={editorContainer}
			class="nodrag min-h-[3rem] rounded border border-gray-300"
			style="height: {contentHeight ? Math.min(contentHeight, maxHeight) : 'auto'}px;"
		></div>
	</div>
</div>

<style>
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
	/* Enable transition on height */
	.transition-height {
		transition: height 0.2s ease-in-out;
	}
	/* Ensure editor container takes up space */
	:global(.monaco-editor) {
		height: 100% !important;
		width: 100% !important;
	}
</style>
