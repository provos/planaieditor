<script lang="ts">
	import {
		llmConfigs,
		llmConfigsFromCode,
		getLLMConfigById,
		getLLMConfigFromCodeById,
		type LLMConfigBasic
	} from '$lib/stores/llmConfigsStore';
	import { getProviderVisuals, type ProviderVisuals } from '$lib/utils/providerVisuals';

	type ConfigChangeEvent = {
		configName?: string;
		configFromCode?: Record<string, any>;
		configVar?: string;
	};

	const {
		id,
		initialConfigName = undefined,
		initialConfigFromCode = undefined,
		initialConfigVar = undefined,
		onChange = undefined
	} = $props<{
		id: string;
		initialConfigName?: string;
		initialConfigFromCode?: Record<string, any>;
		initialConfigVar?: string;
		onChange?: (changes: ConfigChangeEvent) => void;
	}>();

	// State for the combined selection identifier (e.g., "user:uuid" or "code:uuid")
	let selectedConfigName = $state<string | undefined>(initialConfigName || initialConfigVar);

	// Combine user and code configs for the dropdown
	const combinedConfigs = $derived<LLMConfigBasic[]>([...$llmConfigs, ...$llmConfigsFromCode]);

	// Helper to get visuals for a given identifier
	function getVisualsForIdentifier(identifier: string | undefined): ProviderVisuals | null {
		if (!identifier) return null;
		const config = combinedConfigs.find((c) => c.name === identifier);
		if (!config) return null;

		let provider: string | undefined;
		if (config.source !== 'code') {
			const visualConfig = getLLMConfigById(config.id);
			provider = visualConfig?.provider;
		}

		return getProviderVisuals(provider as any);
	}

	// Reactive visuals based on the selected identifier
	let selectedConfigVisuals = $derived(getVisualsForIdentifier(selectedConfigName));

	// Effect to emit changes back to parent
	$effect(() => {
		if (!onChange) return;

		if (selectedConfigName) {
			let sourceConfig = combinedConfigs.find((c) => c.name === selectedConfigName);
			if (!sourceConfig) return;

			if (sourceConfig.source !== 'code') {
				const config = getLLMConfigById(sourceConfig.id);
				if (config) {
					onChange({
						configName: config.name,
						configFromCode: undefined,
						configVar: undefined
					});
				}
			} else {
				const config = getLLMConfigFromCodeById(sourceConfig.id);
				if (config) {
					onChange({
						configName: undefined,
						configFromCode: config.llmConfigFromCode,
						configVar: config.name
					});
				}
			}
		} else {
			// No selection or invalid identifier
			onChange({
				configName: undefined,
				configFromCode: undefined,
				configVar: undefined
			});
		}
	});

	// Add a function to format the imported LLM config for display
	function formatImportedLLMConfig(config: Record<string, any> | undefined): string {
		if (!config) return '';

		const parts = [];

		if (config.provider) parts.push(`Provider: ${config.provider.value}`);
		if (config.model_name) parts.push(`Model: ${config.model_name.value}`);
		if (config.max_tokens) parts.push(`Max Tokens: ${config.max_tokens.value}`);
		if (config.host) parts.push(`Host: ${config.host.value}`);

		return parts.join(', ');
	}
</script>

<div class="mb-2 flex-none">
	<label for="llm-config-{id}" class="label flex-none">LLM Config</label>
	<div
		class="mt-1 flex items-center gap-2 {initialConfigFromCode ? 'bg-gray-100' : 'bg-green-100'}"
	>
		{#if selectedConfigVisuals}
			<div class="flex-none" title={initialConfigName || initialConfigFromCode?.name}>
				<selectedConfigVisuals.icon size={12} class={selectedConfigVisuals.colorClass} />
			</div>
		{/if}
		<select
			id="llm-config-{id}"
			class="text-2xs nodrag select select-bordered select-sm w-full flex-grow"
			bind:value={selectedConfigName}
		>
			<option value={undefined}>-- Select --</option>
			{#if combinedConfigs.length === 0}
				<option disabled>No configs defined or imported</option>
			{:else}
				{#each combinedConfigs as config (config.id)}
					{#if config.source === 'user'}
						<option value={config.name}>{config.name}</option>
					{:else}
						<option value={config.name}
							>{config.name} ({formatImportedLLMConfig(
								getLLMConfigFromCodeById(config.id)?.llmConfigFromCode
							)})</option
						>
					{/if}
				{/each}
			{/if}
		</select>
	</div>
</div>

<style lang="postcss">
	@reference "tailwindcss";

	.text-2xs {
		font-size: 0.65rem; /* 10.4px */
		line-height: 1rem; /* 16px */
	}

	.label {
		font-size: 0.65rem; /* Apply text-2xs size directly */
		line-height: 1rem; /* Apply text-2xs line-height directly */
		font-weight: 600; /* Corresponds to font-semibold */
		color: rgb(75 85 99); /* Corresponds to text-gray-600 */
	}
</style>
