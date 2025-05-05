<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import ChevronDown from 'phosphor-svelte/lib/ArrowDown';
	import ChevronRight from 'phosphor-svelte/lib/ArrowRight';
	import Trash from 'phosphor-svelte/lib/Trash';
	import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';
	import { tick } from 'svelte';
	import { monacoInstance } from '$lib/stores/monacoStore.svelte'; // Import the shared instance
	import { socketStore } from '$lib/stores/socketStore.svelte';
	import { SocketIOReader, SocketIOWriter } from '$lib/lsp/lsp-utils'; // Import custom reader/writer

	let {
		title = '',
		code,
		language = 'python',
		initialCollapsed = false,
		onUpdate,
		onReset = undefined,
		showReset = false,
		onCollapseToggle,
		maxHeight = 400
	} = $props<{
		title?: string;
		code: string;
		language?: 'python' | 'markdown' | 'json' | 'javascript' | 'typescript';
		initialCollapsed?: boolean;
		onUpdate: (newCode: string) => void;
		onReset?: () => void;
		showReset?: boolean;
		onCollapseToggle?: () => void;
		maxHeight?: number; // Maximum height before scrolling
	}>();

	let collapsed = $state(initialCollapsed);
	let editorContainer: HTMLDivElement | undefined = $state();
	let editor: Monaco.editor.IStandaloneCodeEditor | undefined;
	let contentHeight = $state(0); // Track content height
	let currentCode = $state(code);
	let resizeObserver: ResizeObserver | undefined;
	let languageClient: any | undefined = $state();
	let reader: SocketIOReader | undefined = $state();
	let writer: SocketIOWriter | undefined = $state();
	// State to hold dynamically imported MonacoLanguageClient constructor
	let MonacoLanguageClientConstructor = $state<any | undefined>();

	onDestroy(async () => {
		console.log('[LSP EditableCodeSection] Destroying component...');
		// Stop the language client first
		try {
			await languageClient?.stop();
			console.log('[LSP EditableCodeSection] Language client stopped.');
		} catch (e) {
			console.error('[LSP EditableCodeSection] Error stopping language client:', e);
		}

		// Dispose reader/writer
		try {
			reader?.dispose();
			console.log('[LSP EditableCodeSection] LSP Reader disposed.');
		} catch (e) {
			console.warn('[LSP EditableCodeSection] Error disposing reader:', e);
		}
		try {
			writer?.dispose();
			console.log('[LSP EditableCodeSection] LSP Writer disposed.');
		} catch (e) {
			console.warn('[LSP EditableCodeSection] Error disposing writer:', e);
		}

		// Dispose editor and models
		editor?.dispose();
		console.log('[LSP EditableCodeSection] Monaco editor disposed.');
		// Get models *before* disposing the instance if possible, though often handled by editor dispose
		// monacoInstance.instance?.editor.getModels().forEach((model) => model.dispose());

		resizeObserver?.disconnect(); // Disconnect observer on destroy
		console.log('[LSP EditableCodeSection] Resize observer disconnected.');

		// Clear references
		languageClient = undefined;
		reader = undefined;
		writer = undefined;
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
				fontSize: 11,
				minimap: { enabled: false },
				scrollBeyondLastLine: false,
				scrollbar: {
					vertical: 'auto',
					horizontalScrollbarSize: 8,
					verticalScrollbarSize: 8
				},
				lineHeight: 18,
				theme: 'vs-light',
				fixedOverflowWidgets: false
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

	// Effect to setup LSP connection when ready
	$effect(() => {
		const monaco = monacoInstance.instance;
		const socket = socketStore.socket;

		// Conditions to check before setting up LSP
		if (
			language === 'python' && // Only for Python
			socketStore.isConnected &&
			socket && // Socket must be connected and available
			monaco && // Monaco must be loaded
			editor && // Editor must be created
			editorContainer && // Container must be available
			!languageClient // LSP client shouldn't already exist for this editor
		) {
			console.log(`[LSP EditableCodeSection ${title}] Conditions met, setting up LSP...`);

			// Run the import and setup logic in an async IIFE
			void (async () => {
				let ClientConstructor = MonacoLanguageClientConstructor;

				// Dynamically import the MonacoLanguageClient if not already loaded
				if (!ClientConstructor) {
					console.log(
						`[LSP EditableCodeSection ${title}] Dynamically importing MonacoLanguageClient...`
					);
					try {
						const clientModule = await import('monaco-languageclient');
						MonacoLanguageClientConstructor = clientModule.MonacoLanguageClient;
						ClientConstructor = MonacoLanguageClientConstructor; // Update local var
						console.log(
							`[LSP EditableCodeSection ${title}] MonacoLanguageClient imported successfully.`
						);
					} catch (err) {
						console.error(
							`[LSP EditableCodeSection ${title}] Failed to dynamically import MonacoLanguageClient:`,
							err
						);
						return; // Stop if import failed
					}
				}

				// --- Proceed only if services are initialized, Client Constructor is loaded and state is still valid ---
				if (
					ClientConstructor &&
					socketStore.isConnected &&
					editor // Ensure editor still exists
				) {
					console.log(
						`[LSP EditableCodeSection ${title}] MonacoLanguageClient constructor available and state valid, proceeding with setup.`
					);

					// Dispose existing reader/writer if any (safety net)
					reader?.dispose();
					writer?.dispose();

					// Create custom SocketIO reader/writer
					// Ensure socket is still valid before using
					if (!socketStore.socket) {
						console.error(`[LSP EditableCodeSection ${title}] Socket became null during setup.`);
						return;
					}
					reader = new SocketIOReader(socketStore.socket);
					writer = new SocketIOWriter(socketStore.socket);
					const transports: MessageTransports = { reader, writer };

					// Function to create the language client
					function createLanguageClient(
						transports: MessageTransports,
						monacoInstanceRef: typeof Monaco
					): MonacoLanguageClientType {
						const clientOptions: LanguageClientOptions = {
							documentSelector: [language],
							errorHandler: {
								error: () => ({ action: ErrorAction.Continue }),
								closed: () => ({ action: CloseAction.DoNotRestart })
							},
							workspaceFolder: {
								uri: monacoInstanceRef.Uri.parse('/workspace'),
								name: 'workspace',
								index: 0
							},
							initializationOptions: {}
						};

						// Use the dynamically imported constructor
						// Assert ClientConstructor is defined because of the check above
						return new ClientConstructor!({
							name: `Python Language Client for ${title}`,
							clientOptions: clientOptions,
							messageTransports: transports
						});
					}

					// Create and start the client
					try {
						// Ensure monaco instance is still valid
						if (!monacoInstance.instance) {
							console.error(
								`[LSP EditableCodeSection ${title}] Monaco instance became null during setup.`
							);
							return;
						}
						languageClient = createLanguageClient(transports, monaco);
						console.log(`[LSP EditableCodeSection ${title}] Language client created.`);

						const startPromise = languageClient.start();
						startPromise
							.then(() => {
								console.log(
									`[LSP EditableCodeSection ${title}] Language client started successfully.`
								);
							})
							.catch((error) => {
								console.error(
									`[LSP EditableCodeSection ${title}] Failed to start language client:`,
									error
								);
								// Clean up partially created client on start failure
								languageClient = undefined;
								reader?.dispose();
								writer?.dispose();
								reader = undefined;
								writer = undefined;
							});

						// Handle reader closure (likely due to socket disconnect)
						reader.onClose(() => {
							console.warn(
								`[LSP EditableCodeSection ${title}] LSP Reader closed. Stopping client.`
							);
							languageClient
								?.stop()
								.catch((e) =>
									console.error(
										`[LSP EditableCodeSection ${title}] Error stopping client on reader close:`,
										e
									)
								);
							// Clear references as the connection is gone
							languageClient = undefined;
							reader = undefined; // Writer might still be technically open, but useless
							writer = undefined;
						});
					} catch (error) {
						console.error(
							`[LSP EditableCodeSection ${title}] Error creating language client:`,
							error
						);
						// Ensure cleanup if creation fails
						reader?.dispose();
						writer?.dispose();
						reader = undefined;
						writer = undefined;
						languageClient = undefined;
					}
				} else {
					console.log(
						`[LSP EditableCodeSection ${title}] MonacoLanguageClient constructor not loaded or state changed, skipping setup.`
					);
				}
			})(); // Immediately invoke the async IIFE
		} else if (languageClient && (!socketStore.isConnected || language !== 'python')) {
			// If connection drops or language changes away from Python, stop the existing client
			console.log(
				`[LSP EditableCodeSection ${title}] Conditions no longer met (connected: ${socketStore.isConnected}, lang: ${language}). Stopping LSP client.`
			);
			languageClient.stop().catch((e) => console.error('Error stopping client:', e));
			reader?.dispose(); // Dispose reader/writer too
			writer?.dispose();
			languageClient = undefined;
			reader = undefined;
			writer = undefined;
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
	}

	function toggleCollapse() {
		collapsed = !collapsed;
		onCollapseToggle?.();
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

<div class="flex h-full min-h-0 flex-col">
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

	<div
		class="min-w-[60ch] {collapsed ? 'hidden h-0' : 'flex-grow'} transition-height p-1 duration-200"
	>
		<div
			bind:this={editorContainer}
			class="min-h-[3rem] w-full rounded border border-gray-300"
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
