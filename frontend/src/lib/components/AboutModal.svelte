<script lang="ts">
	import X from 'phosphor-svelte/lib/X';
	import { onMount } from 'svelte';

	interface Props {
		show: boolean;
		onClose: () => void;
	}

	const { show = false, onClose }: Props = $props();

	function closeModal() {
		onClose();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			closeModal();
		}
	}

	onMount(() => {
		if (show) {
			document.addEventListener('keydown', handleKeydown);
		}
		return () => {
			document.removeEventListener('keydown', handleKeydown);
		};
	});

	// Reactive effect to manage event listeners when show changes
	$effect(() => {
		if (show) {
			document.addEventListener('keydown', handleKeydown);
			// Focus trap - focus the modal when it opens
			const modal = document.querySelector('[data-modal="about"]') as HTMLElement;
			if (modal) {
				modal.focus();
			}
		} else {
			document.removeEventListener('keydown', handleKeydown);
		}
	});
</script>

{#if show}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
		onclick={closeModal}
		onkeydown={(e) => e.key === 'Enter' && closeModal()}
		role="dialog"
		aria-modal="true"
		aria-labelledby="about-title"
		tabindex="0"
	>
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<div
			class="relative mx-4 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl transition-all duration-300 ease-out"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="document"
			data-modal="about"
			tabindex="-1"
		>
			<!-- Header -->
			<div class="relative px-8 pt-8 pb-6">
				<button
					class="absolute top-6 right-6 flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-500 transition-colors hover:bg-gray-200 hover:text-gray-700 focus:ring-2 focus:ring-blue-500 focus:outline-none"
					onclick={closeModal}
					aria-label="Close modal"
				>
					<X size={16} weight="bold" />
				</button>

				<div class="text-center">
					<h1 id="about-title" class="mb-2 text-3xl font-bold text-gray-900">PlanAI Editor</h1>
					<div
						class="mx-auto h-1 w-24 rounded-full bg-gradient-to-r from-blue-500 to-purple-600"
					></div>
				</div>
			</div>

			<!-- Content -->
			<div class="space-y-8 px-8 pb-8">
				<!-- Purpose Section -->
				<div class="text-center">
					<p class="mx-auto max-w-xl text-lg leading-relaxed text-gray-700">
						A graphical user interface for visually building and managing AI workflows using the
						<a
							href="https://getplanai.com/"
							target="_blank"
							rel="noopener noreferrer"
							class="font-semibold text-blue-600 underline decoration-blue-300 underline-offset-2 transition-colors hover:text-blue-800"
							>PlanAI</a
						> framework. Design and test complex agentic workflows with an intuitive node-based interface,
						then export them to Python code for production.
					</p>
				</div>

				<!-- Technologies Section -->
				<div class="rounded-xl bg-gradient-to-br from-gray-50 to-gray-100 p-6">
					<h2 class="mb-4 text-center text-xl font-semibold text-gray-900">
						Built with Modern Technologies
					</h2>

					<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
						<!-- Frontend Technologies -->
						<div class="space-y-3">
							<h3 class="text-sm font-medium tracking-wide text-gray-600 uppercase">Frontend</h3>
							<div class="space-y-2">
								<div class="flex items-center space-x-3">
									<div class="h-2 w-2 rounded-full bg-orange-500"></div>
									<a
										href="https://svelte.dev/"
										target="_blank"
										rel="noopener noreferrer"
										class="text-gray-700 transition-colors hover:text-blue-600"
										>Svelte 5 & SvelteKit</a
									>
								</div>
								<div class="flex items-center space-x-3">
									<div class="h-2 w-2 rounded-full bg-blue-500"></div>
									<a
										href="https://svelteflow.dev/"
										target="_blank"
										rel="noopener noreferrer"
										class="text-gray-700 transition-colors hover:text-blue-600">SvelteFlow</a
									>
								</div>
								<div class="flex items-center space-x-3">
									<div class="h-2 w-2 rounded-full bg-blue-600"></div>
									<a
										href="https://microsoft.github.io/monaco-editor/"
										target="_blank"
										rel="noopener noreferrer"
										class="text-gray-700 transition-colors hover:text-blue-600">Monaco Editor</a
									>
								</div>
								<div class="flex items-center space-x-3">
									<div class="h-2 w-2 rounded-full bg-cyan-500"></div>
									<a
										href="https://tailwindcss.com/"
										target="_blank"
										rel="noopener noreferrer"
										class="text-gray-700 transition-colors hover:text-blue-600">TailwindCSS</a
									>
								</div>
								<div class="flex items-center space-x-3">
									<div class="h-2 w-2 rounded-full bg-gray-500"></div>
									<a
										href="https://bits-ui.com/"
										target="_blank"
										rel="noopener noreferrer"
										class="text-gray-700 transition-colors hover:text-blue-600">bits-ui</a
									>
								</div>
								<div class="flex items-center space-x-3">
									<div class="h-2 w-2 rounded-full bg-green-600"></div>
									<a
										href="https://phosphoricons.com/"
										target="_blank"
										rel="noopener noreferrer"
										class="text-gray-700 transition-colors hover:text-blue-600">Phosphor Icons</a
									>
								</div>
							</div>
						</div>

						<!-- Backend Technologies -->
						<div class="space-y-3">
							<h3 class="text-sm font-medium tracking-wide text-gray-600 uppercase">Backend</h3>
							<div class="space-y-2">
								<div class="flex items-center space-x-3">
									<div class="h-2 w-2 rounded-full bg-yellow-600"></div>
									<a
										href="https://python.org/"
										target="_blank"
										rel="noopener noreferrer"
										class="text-gray-700 transition-colors hover:text-blue-600">Python 3.10+</a
									>
								</div>
								<div class="flex items-center space-x-3">
									<div class="h-2 w-2 rounded-full bg-red-500"></div>
									<a
										href="https://flask.palletsprojects.com/"
										target="_blank"
										rel="noopener noreferrer"
										class="text-gray-700 transition-colors hover:text-blue-600">Flask</a
									>
								</div>
								<div class="flex items-center space-x-3">
									<div class="h-2 w-2 rounded-full bg-green-500"></div>
									<a
										href="https://flask-socketio.readthedocs.io/"
										target="_blank"
										rel="noopener noreferrer"
										class="text-gray-700 transition-colors hover:text-blue-600">Flask-SocketIO</a
									>
								</div>
								<div class="flex items-center space-x-3">
									<div class="h-2 w-2 rounded-full bg-purple-500"></div>
									<a
										href="https://getplanai.com/"
										target="_blank"
										rel="noopener noreferrer"
										class="text-gray-700 transition-colors hover:text-blue-600">PlanAI Framework</a
									>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- License & Support Section -->
				<div class="border-t border-gray-200 pt-6">
					<div class="space-y-4 text-center">
						<div class="text-sm text-gray-600">
							Report bugs or feature requests at
							<a
								href="https://github.com/provos/planaieditor/issues"
								target="_blank"
								rel="noopener noreferrer"
								class="text-blue-600 underline decoration-blue-300 underline-offset-2 transition-colors hover:text-blue-800"
								>GitHub Issues</a
							>
						</div>
						<div class="mx-auto max-w-md text-xs text-gray-400">
							© 2025 Niels Provos. This software is released under the Apache License, Version 2.0.
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	/* Custom scrollbar for the modal */
	div[data-modal='about'] {
		scrollbar-width: thin;
		scrollbar-color: #d1d5db #f3f4f6;
	}

	div[data-modal='about']::-webkit-scrollbar {
		width: 6px;
	}

	div[data-modal='about']::-webkit-scrollbar-track {
		background: #f3f4f6;
	}

	div[data-modal='about']::-webkit-scrollbar-thumb {
		background: #d1d5db;
		border-radius: 3px;
	}

	div[data-modal='about']::-webkit-scrollbar-thumb:hover {
		background: #9ca3af;
	}
</style>
