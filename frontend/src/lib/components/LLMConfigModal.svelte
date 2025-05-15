<script lang="ts">
	import { backendUrl } from '$lib/utils/backendUrl';
	import {
		X,
		FloppyDisk,
		PencilSimple,
		Trash,
		Spinner,
		Code,
		CaretDown,
		Check
	} from 'phosphor-svelte';
	import { Combobox, Label, RadioGroup } from 'bits-ui';
	import {
		llmConfigs,
		addLLMConfig,
		updateLLMConfig,
		deleteLLMConfig,
		validLLMProviders,
		llmConfigsFromCode,
		type LLMConfig
	} from '$lib/stores/llmConfigsStore';
	import { getProviderVisuals } from '$lib/utils/providerVisuals';

	// Props to control visibility
	let { showModal = $bindable() } = $props<{ showModal: boolean }>();

	// Component State
	let editingConfigId = $state<string | null>(null);
	let isAddingNew = $state<boolean>(false);
	let formState = $state<Partial<LLMConfig>>({}); // Use Partial for add/edit form
	let availableModels = $state<string[]>([]);
	let modelLoading = $state<boolean>(false);
	let modelError = $state<string | null>(null);
	let generalError = $state<string | null>(null);

	// Search values for comboboxes
	let providerSearchValue = $state('');
	let modelSearchValue = $state('');

	// Filtered options for comboboxes
	const filteredProviders = $derived(
		providerSearchValue === ''
			? validLLMProviders
			: validLLMProviders.filter((provider) =>
					provider.toLowerCase().includes(providerSearchValue.toLowerCase())
				)
	);

	const filteredModels = $derived(
		modelSearchValue === ''
			? availableModels
			: availableModels.filter((model) =>
					model.toLowerCase().includes(modelSearchValue.toLowerCase())
				)
	);

	// Reset form state
	function resetForm() {
		formState = {};
		availableModels = [];
		modelLoading = false;
		modelError = null;
		generalError = null;
		isAddingNew = false;
		editingConfigId = null;
		providerSearchValue = '';
		modelSearchValue = '';
		formState.json_mode = undefined;
		formState.structured_outputs = undefined;
	}

	// Fetch models when provider changes
	$effect(() => {
		const provider = formState.provider;
		if (provider) {
			fetchModelsForProvider(provider); // async function does not trigger reactivity
		} else {
			availableModels = []; // Clear models if provider is cleared
		}
	});

	async function fetchModelsForProvider(provider: LLMConfig['provider']) {
		modelLoading = true;
		modelError = null;
		availableModels = []; // Clear previous models
		console.log(`Fetching models for provider: ${provider}`);
		try {
			const response = await fetch(`${backendUrl}/api/llm/list-models?provider=${provider}`);
			const data = await response.json();
			if (response.ok && data.success) {
				availableModels = data.models || [];
				console.log(`Received models: ${availableModels}`);
				if (availableModels.length === 0) {
					modelError = `No models found for ${provider}. Ensure the backend has access and necessary keys/setup.`;
				}
			} else {
				const errorMsg = data.error || `Failed to fetch models (HTTP ${response.status})`;
				console.error('Error fetching models:', errorMsg);
				modelError = errorMsg;
			}
		} catch (err: any) {
			console.error('Network error fetching models:', err);
			modelError = `Network error: ${err.message}`; // Show network errors too
		}
		if (formState.modelId && !availableModels.includes(formState.modelId)) {
			formState.modelId = undefined; // Reset selected model
		}

		modelLoading = false;
	}

	// Start editing an existing config
	function startEdit(config: LLMConfig) {
		resetForm();
		editingConfigId = config.id;
		// Deep copy the config to avoid mutating the store directly
		console.log(`Starting edit for config: ${JSON.stringify(config)}`);
		formState = JSON.parse(JSON.stringify(config));
		// Model fetch will be triggered by the $effect
	}

	// Start adding a new config
	function startAddNew() {
		resetForm();
		isAddingNew = true;
	}

	// Cancel add/edit
	function cancelEdit() {
		resetForm();
	}

	// Save configuration (Add or Update)
	function saveConfig() {
		generalError = null; // Clear previous errors
		// Basic Validation
		if (!formState.name || !formState.provider || !formState.modelId) {
			generalError = 'Name, Provider, and Model ID are required.';
			return;
		}

		try {
			if (editingConfigId) {
				// Update existing config
				updateLLMConfig(formState as LLMConfig); // Cast to full LLMConfig
			} else {
				// Add new config
				addLLMConfig(formState as Omit<LLMConfig, 'id'>); // Cast to exclude id
			}
			resetForm(); // Clear form on success
		} catch (e: any) {
			generalError = e.message || 'Failed to save configuration.';
		}
	}

	// Delete configuration
	function handleDelete(id: string) {
		if (confirm('Are you sure you want to delete this LLM configuration?')) {
			try {
				deleteLLMConfig(id);
				// If deleting the one being edited, reset the form
				if (editingConfigId === id) {
					resetForm();
				}
			} catch (e: any) {
				generalError = e.message || 'Failed to delete configuration.';
			}
		}
	}

	// Close the modal
	function closeModal() {
		resetForm();
		showModal = false;
	}

	// Add a global keydown listener for the Escape key when the modal is shown
	$effect(() => {
		if (showModal) {
			const handleKeydown = (e: KeyboardEvent) => {
				if (e.key === 'Escape') {
					closeModal();
				}
			};

			window.addEventListener('keydown', handleKeydown);

			// Cleanup function to remove the listener when the modal is hidden
			return () => {
				window.removeEventListener('keydown', handleKeydown);
			};
		}
	});

	// Function to format the imported LLM config for display (similar to LLMTaskWorkerNode)
	function formatImportedLLMConfigDetails(configData: Record<string, any>): string {
		const parts = [];
		if (configData.provider) parts.push(`Provider: ${configData.provider.value}`);
		if (configData.model_name) parts.push(`Model: ${configData.model_name.value}`);
		if (configData.max_tokens) parts.push(`Max Tokens: ${configData.max_tokens.value}`);
		if (configData.host) parts.push(`Host: ${configData.host.value}`); // Used by Ollama
		if (configData.baseUrl) parts.push(`Base URL: ${configData.baseUrl.value}`); // Used by OpenAI
		if (configData.remote_hostname) parts.push(`Remote Host: ${configData.remote_hostname.value}`);
		if (configData.remote_username) parts.push(`Remote User: ${configData.remote_username.value}`);
		if (configData.json_mode) parts.push(`JSON Mode: ${configData.json_mode.value}`);
		if (configData.structured_outputs)
			parts.push(`Structured Outputs: ${configData.structured_outputs.value}`);

		return parts.join(', ');
	}

	type RadioOption = 'true' | 'false' | 'unset';

	function getRadioValue(value: boolean | undefined): RadioOption {
		if (value === true) return 'true';
		if (value === false) return 'false';
		return 'unset';
	}

	function setRadioValue(newValue: RadioOption): boolean | undefined {
		if (newValue === 'true') return true;
		if (newValue === 'false') return false;
		return undefined;
	}

	function getJsonModeRadioValue() {
		return getRadioValue(formState.json_mode);
	}

	function setJsonModeRadioValue(newValue: RadioOption) {
		formState.json_mode = setRadioValue(newValue);
	}

	function getStructuredOutputsRadioValue() {
		return getRadioValue(formState.structured_outputs);
	}

	function setStructuredOutputsRadioValue(newValue: RadioOption) {
		formState.structured_outputs = setRadioValue(newValue);
	}
	// --- End RadioGroup Helpers ---
</script>

{#if showModal}
	<!-- Modal Backdrop -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div
		class="fixed inset-0 z-40 bg-gray-900/50 backdrop-blur-sm"
		onclick={closeModal}
		role="button"
		tabindex="0"
	></div>

	<!-- Modal Content -->
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
		<div class="relative w-full max-w-3xl rounded-lg bg-white p-6 shadow-xl">
			<!-- Close Button -->
			<button
				class="absolute top-4 right-4 text-gray-500 hover:text-red-800"
				onclick={closeModal}
				title="Close"
			>
				<X size={24} />
			</button>

			<h2 class="mb-6 text-xl font-semibold text-gray-800">Manage LLM Configurations</h2>

			<!-- Configuration List -->
			<div class="mb-6 max-h-60 overflow-y-auto rounded border border-gray-200">
				<table class="min-w-full divide-y divide-gray-200">
					<thead class="sticky top-0 bg-gray-50">
						<tr>
							<th
								class="w-8 px-3 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
								title="Provider"
							></th>
							<th
								class="px-4 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
								>Name</th
							>
							<th
								class="px-4 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
								>Provider</th
							>
							<th
								class="px-4 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
								>Model ID</th
							>
							<th
								class="px-4 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
								>Actions</th
							>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200 bg-white">
						{#if $llmConfigs.length === 0}
							<tr>
								<td colspan="5" class="px-4 py-3 text-center text-sm text-gray-500"
									>No configurations defined.</td
								>
							</tr>
						{/if}
						{#each $llmConfigs as config (config.id)}
							{@const visuals = getProviderVisuals(config.provider)}
							<tr class:bg-blue-50={editingConfigId === config.id}>
								<td class="px-3 py-2 text-sm whitespace-nowrap">
									<visuals.icon size={18} class={visuals.colorClass} />
								</td>
								<td class="px-4 py-2 text-sm font-medium whitespace-nowrap text-gray-900"
									>{config.name}</td
								>
								<td class="px-4 py-2 text-sm whitespace-nowrap text-gray-500">{config.provider}</td>
								<td class="px-4 py-2 text-sm whitespace-nowrap text-gray-500">{config.modelId}</td>
								<td class="px-4 py-2 text-sm font-medium whitespace-nowrap">
									<button
										class="mr-2 text-blue-600 hover:text-blue-800"
										onclick={() => startEdit(config)}
										title="Edit"
										disabled={editingConfigId === config.id || isAddingNew}
									>
										<PencilSimple size={18} />
									</button>
									<button
										class="text-red-600 hover:text-red-800"
										onclick={() => handleDelete(config.id)}
										title="Delete"
										disabled={editingConfigId === config.id || isAddingNew}
									>
										<Trash size={18} />
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			<!-- Imported Configurations List (Read-only) -->
			{#if $llmConfigsFromCode.length > 0}
				<div class="mb-4 border-t border-gray-300 pt-4">
					<h3 class="mb-2 flex items-center text-base font-semibold text-gray-700">
						Imported from Code
					</h3>
					<div class="max-h-40 overflow-y-auto rounded border border-gray-200 bg-gray-50/50">
						<table class="min-w-full divide-y divide-gray-200">
							<thead class="sticky top-0 bg-gray-100">
								<tr>
									<th
										class="w-8 px-3 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
										title="Imported"
									></th>
									<th
										class="px-4 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
										>Variable Name</th
									>
									<th
										class="px-4 py-2 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
										>Details</th
									>
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-200 bg-white">
								{#each $llmConfigsFromCode as config (config.id)}
									<tr>
										<td class="px-3 py-2 text-sm whitespace-nowrap text-gray-400">
											<Code size={18} />
										</td>
										<td class="px-4 py-2 text-sm font-medium whitespace-nowrap text-gray-800"
											>{config.name}</td
										>
										<td class="px-4 py-2 text-sm text-gray-600">
											{formatImportedLLMConfigDetails(config.llmConfigFromCode)}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			{/if}

			<!-- Add New / Edit Form -->
			{#if isAddingNew || editingConfigId}
				<div class="mb-4 rounded border border-gray-200 bg-gray-50 p-4">
					<div class="mb-4 flex items-center justify-between">
						<h3 class="text-lg font-medium text-gray-700">
							{isAddingNew ? 'Add New Configuration' : 'Edit Configuration'}
						</h3>
						{#if formState.provider}
							{@const formVisuals = getProviderVisuals(formState.provider)}
							<div title={formState.provider} class="ml-2">
								<formVisuals.icon size={24} class={formVisuals.colorClass} />
							</div>
						{/if}
					</div>
					<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
						<!-- Name -->
						<div>
							<label for="config-name" class="mb-1 block text-sm font-medium text-gray-700"
								>Name*</label
							>
							<input
								type="text"
								id="config-name"
								class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
								bind:value={formState.name}
								required
							/>
						</div>

						<!-- Provider -->
						<div>
							<label for="config-provider" class="mb-1 block text-sm font-medium text-gray-700"
								>Provider*</label
							>
							<Combobox.Root
								type="single"
								name="provider"
								bind:value={formState.provider}
								onOpenChange={(o) => {
									if (!o) providerSearchValue = '';
								}}
							>
								<div class="relative">
									<Combobox.Input
										id="config-provider"
										oninput={(e) => (providerSearchValue = e.currentTarget.value)}
										class="block w-full rounded-md border-gray-300 pr-8 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
										placeholder="Search for a provider ..."
										defaultValue={formState.provider}
									/>
									<Combobox.Trigger class="absolute top-1/2 right-2 -translate-y-1/2">
										<CaretDown size={16} class="text-gray-500" />
									</Combobox.Trigger>
								</div>
								<Combobox.Portal>
									<Combobox.Content
										class="z-50 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-sm shadow-lg ring-1 ring-black/5"
										sideOffset={4}
									>
										<Combobox.Viewport>
											{#each filteredProviders as provider (provider)}
												<Combobox.Item
													value={provider}
													label={provider}
													class="relative flex cursor-default items-center rounded-sm py-1.5 pr-2 pl-8 outline-none select-none data-highlighted:bg-indigo-100 data-highlighted:text-indigo-900"
												>
													{#snippet children({ selected })}
														{provider}
														{#if selected}
															<div class="absolute top-1/2 left-2 -translate-y-1/2">
																<Check size={16} class="text-indigo-600" />
															</div>
														{/if}
													{/snippet}
												</Combobox.Item>
											{:else}
												<span class="block px-4 py-2 text-sm text-gray-500">
													No provider found
												</span>
											{/each}
										</Combobox.Viewport>
									</Combobox.Content>
								</Combobox.Portal>
							</Combobox.Root>
						</div>

						<!-- Model ID -->
						<div class="relative">
							<label for="config-modelId" class="mb-1 block text-sm font-medium text-gray-700"
								>Model ID*</label
							>
							<Combobox.Root
								type="single"
								name="modelId"
								bind:value={formState.modelId}
								onOpenChange={(o) => {
									if (!o) modelSearchValue = '';
								}}
								disabled={!formState.provider || modelLoading || !!modelError}
							>
								<div class="relative">
									<Combobox.Input
										id="config-modelId"
										oninput={(e) => (modelSearchValue = e.currentTarget.value)}
										class="block w-full rounded-md border-gray-300 pr-8 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
										placeholder="Search for a model ..."
										disabled={!formState.provider || modelLoading || !!modelError}
										defaultValue={formState.modelId}
									/>
									<Combobox.Trigger
										class="absolute top-1/2 right-2 -translate-y-1/2"
										disabled={!formState.provider || modelLoading || !!modelError}
									>
										{#if modelLoading}
											<Spinner size={16} class="animate-spin text-indigo-600" />
										{:else}
											<CaretDown size={16} class="text-gray-500" />
										{/if}
									</Combobox.Trigger>
								</div>
								{#if formState.provider && !modelLoading && !modelError}
									<Combobox.Portal>
										<Combobox.Content
											class="z-50 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-sm shadow-lg ring-1 ring-black/5"
											sideOffset={4}
										>
											<Combobox.Viewport>
												{#each filteredModels as modelName (modelName)}
													<Combobox.Item
														value={modelName}
														label={modelName}
														class="relative flex cursor-default items-center rounded-sm py-1.5 pr-2 pl-8 outline-none select-none data-highlighted:bg-indigo-100 data-highlighted:text-indigo-900"
													>
														{#snippet children({ selected })}
															{modelName}
															{#if selected}
																<div class="absolute top-1/2 left-2 -translate-y-1/2">
																	<Check size={16} class="text-indigo-600" />
																</div>
															{/if}
														{/snippet}
													</Combobox.Item>
												{:else}
													<span class="block px-4 py-2 text-sm text-gray-500">
														No models found
													</span>
												{/each}
											</Combobox.Viewport>
										</Combobox.Content>
									</Combobox.Portal>
								{/if}
							</Combobox.Root>
							{#if modelError}
								<p class="mt-1 text-xs text-red-600">{modelError}</p>
							{/if}
						</div>

						<!-- Max Tokens -->
						<div>
							<label for="config-max_tokens" class="mb-1 block text-sm font-medium text-gray-700"
								>Max Tokens (Optional)</label
							>
							<input
								type="number"
								id="config-max_tokens"
								class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
								bind:value={formState.max_tokens}
								min="1"
							/>
						</div>

						<!-- Provider Specific Fields -->
						{#if formState.provider === 'ollama' || formState.provider === 'openai'}
							<div>
								<label for="config-baseUrl" class="mb-1 block text-sm font-medium text-gray-700"
									>Base URL (Optional)</label
								>
								<input
									type="url"
									id="config-baseUrl"
									class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
									bind:value={formState.baseUrl}
									placeholder="e.g., http://localhost:11434 or custom OpenAI endpoint"
								/>
							</div>
						{/if}
						{#if formState.provider === 'remote_ollama'}
							<div>
								<label
									for="config-remoteHostname"
									class="mb-1 block text-sm font-medium text-gray-700">Remote Hostname*</label
								>
								<input
									type="text"
									id="config-remoteHostname"
									class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
									bind:value={formState.remoteHostname}
									required
								/>
							</div>
							<div>
								<label
									for="config-remoteUsername"
									class="mb-1 block text-sm font-medium text-gray-700">Remote Username*</label
								>
								<input
									type="text"
									id="config-remoteUsername"
									class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
									bind:value={formState.remoteUsername}
									required
								/>
							</div>
						{/if}

						<!-- JSON Mode -->
						<div class="col-span-1 md:col-span-2">
							<label for="config-json_mode" class="mb-1 block text-sm font-medium text-gray-700"
								>JSON Mode</label
							>
							<RadioGroup.Root
								id="config-json_mode"
								bind:value={getJsonModeRadioValue, setJsonModeRadioValue}
								class="mt-2 flex space-x-4"
								aria-label="JSON Mode"
							>
								{#each [{ value: 'unset', label: 'Default', id: 'json-unset' }, { value: 'true', label: 'True', id: 'json-true' }, { value: 'false', label: 'False', id: 'json-false' }] as item}
									<div class="flex items-center">
										<RadioGroup.Item
											id={item.id}
											value={item.value}
											class="peer size-4 rounded-full border border-gray-300 text-indigo-600 focus:ring-indigo-500 data-[state=checked]:border-indigo-500 data-[state=checked]:bg-indigo-100"
										>
											{#snippet children({ checked })}
												{#if checked}
													<div class="flex items-center justify-center">
														<div class="size-1.5 rounded-full bg-indigo-600"></div>
													</div>
												{/if}
											{/snippet}
										</RadioGroup.Item>
										<Label.Root
											for={item.id}
											class="ml-2 block text-sm text-gray-700 peer-data-[state=checked]:font-medium"
											>{item.label}</Label.Root
										>
									</div>
								{/each}
							</RadioGroup.Root>
						</div>

						<!-- Structured Outputs -->
						<div class="col-span-1 md:col-span-2">
							<label
								for="config-structured_outputs"
								class="mb-1 block text-sm font-medium text-gray-700">Structured Outputs</label
							>
							<RadioGroup.Root
								id="config-structured_outputs"
								bind:value={getStructuredOutputsRadioValue, setStructuredOutputsRadioValue}
								class="mt-2 flex space-x-4"
								aria-label="Structured Outputs"
							>
								{#each [{ value: 'unset', label: 'Default', id: 'structured-unset' }, { value: 'true', label: 'True', id: 'structured-true' }, { value: 'false', label: 'False', id: 'structured-false' }] as item}
									<div class="flex items-center">
										<RadioGroup.Item
											id={item.id}
											value={item.value}
											class="peer size-4 rounded-full border border-gray-300 text-indigo-600 focus:ring-indigo-500 data-[state=checked]:border-indigo-500 data-[state=checked]:bg-indigo-100"
										>
											{#snippet children({ checked })}
												{#if checked}
													<div class="flex items-center justify-center">
														<div class="size-1.5 rounded-full bg-indigo-600"></div>
													</div>
												{/if}
											{/snippet}
										</RadioGroup.Item>
										<Label.Root
											for={item.id}
											class="ml-2 block text-sm text-gray-700 peer-data-[state=checked]:font-medium"
											>{item.label}</Label.Root
										>
									</div>
								{/each}
							</RadioGroup.Root>
						</div>
					</div>
					<!-- Form Actions -->
					<div class="mt-5 flex justify-end gap-3">
						{#if generalError}
							<p class="mr-auto text-sm text-red-600">Error: {generalError}</p>
						{/if}
						<button
							type="button"
							class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
							onclick={cancelEdit}
						>
							Cancel
						</button>
						<button
							type="button"
							class="inline-flex justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-none"
							onclick={saveConfig}
						>
							<FloppyDisk size={18} class="mr-2 -ml-1" />
							{editingConfigId ? 'Update' : 'Save'} Configuration
						</button>
					</div>
				</div>
			{/if}

			<!-- Add New Button -->
			{#if !isAddingNew && !editingConfigId}
				<div class="flex justify-end">
					<button
						type="button"
						class="inline-flex items-center rounded-md border border-transparent bg-green-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 focus:outline-none"
						onclick={startAddNew}
					>
						Add New Configuration
					</button>
				</div>
			{/if}

			<p class="mt-4 text-xs text-gray-500">
				Note: API keys are not stored here. Ensure the corresponding environment variables (e.g.,
				OPENAI_API_KEY, ANTHROPIC_API_KEY) are set in the backend environment (e.g., via a .env
				file).
			</p>
		</div>
	</div>
{/if}

<style lang="postcss">
	@reference "tailwindcss";
</style>
