import { persisted } from 'svelte-persisted-store';
import type { Writable } from 'svelte/store';

export interface LLMConfigBasic {
    id: string; // Unique ID for the config (e.g., uuid)
    name: string; // User-defined name (e.g., "My OpenAI GPT-4")
}

// Define the structure for an LLM Configuration
export interface LLMConfig extends LLMConfigBasic {
    provider: 'ollama' | 'remote_ollama' | 'openai' | 'anthropic' | 'gemini' | 'openrouter';
    modelId: string; // Specific model ID (e.g., "gpt-4-turbo", "llama3:8b")
    baseUrl?: string; // Optional: For custom OpenAI-compatible or Ollama hosts (maps to 'host' for ollama)
    remoteHostname?: string; // Optional: For remote_ollama
    remoteUsername?: string; // Optional: For remote_ollama
    max_tokens?: number; // Optional: Max tokens override
    // Add other non-sensitive llm_from_config params here if needed (e.g., use_cache boolean?)
}

export interface LLMConfigFromCode extends LLMConfigBasic {
    llmConfigFromCode: Record<string, any>;
}

// Define the valid provider options explicitly for use in UI
export const validLLMProviders: LLMConfig['provider'][] = [
    'ollama',
    'remote_ollama',
    'openai',
    'anthropic',
    'gemini',
    'openrouter'
];

// Create the persisted store, initializing with an empty array
export const llmConfigs: Writable<LLMConfig[]> = persisted<LLMConfig[]>('llmConfigs', []);
export const llmConfigsFromCode: Writable<LLMConfigFromCode[]> = persisted<LLMConfigFromCode[]>('llmConfigsFromCode', []);

// Helper function to add a new configuration
export function addLLMConfig(config: Omit<LLMConfig, 'id'>): string {
    const newId = crypto.randomUUID();
    const newConfig = { ...config, id: newId };
    llmConfigs.update(configs => {
        // Optional: Check for name collision before adding
        if (configs.some(c => c.name === newConfig.name)) {
            throw new Error(`Configuration name \'${newConfig.name}\' already exists.`);
        }
        return [...configs, newConfig];
    });
    return newId; // Return the generated ID
}

// Helper function to update an existing configuration
export function updateLLMConfig(updatedConfig: LLMConfig) {
    llmConfigs.update(configs => {
        // Optional: Check for name collision if name is changed
        const existingIndex = configs.findIndex(c => c.id === updatedConfig.id);
        if (existingIndex !== -1 && configs.some((c, index) => c.name === updatedConfig.name && index !== existingIndex)) {
            throw new Error(`Configuration name \'${updatedConfig.name}\' already exists.`);
        }

        return configs.map(config =>
            config.id === updatedConfig.id ? updatedConfig : config
        );
    });
}

// Helper function to delete a configuration by ID
export function deleteLLMConfig(id: string) {
    llmConfigs.update(configs => configs.filter(config => config.id !== id));
}

// Helper function to get a configuration by ID
export function getLLMConfigById(id: string): LLMConfig | undefined {
    let config: LLMConfig | undefined;
    // Svelte stores are typically accessed via subscription or the $ prefix in components.
    // For a one-off read like this, we can use a temporary subscription.
    const unsubscribe = llmConfigs.subscribe(value => {
        config = value.find(c => c.id === id);
    });
    unsubscribe(); // Immediately unsubscribe
    return config;
}

// Helper function to get a configuration by Name
export function getLLMConfigByName(name: string): LLMConfig | undefined {
    let config: LLMConfig | undefined;
    const unsubscribe = llmConfigs.subscribe(value => {
        config = value.find(c => c.name === name);
    });
    unsubscribe();
    return config;
}

// Helper function to add a new configuration from code - only if the config is not already in the store
export function addLLMConfigFromCode(config: Omit<LLMConfigFromCode, 'id'>): string {
    let existingConfig: LLMConfigFromCode | undefined;
    const unsubscribe = llmConfigsFromCode.subscribe(configs => {
        existingConfig = configs.find((c: LLMConfigFromCode) => c.name === config.name);
    });
    unsubscribe(); // Immediately unsubscribe

    if (existingConfig) {
        return existingConfig.id;
    }
    const newId = crypto.randomUUID();
    const newConfig = { ...config, id: newId };
    llmConfigsFromCode.update(configs => [...configs, newConfig]);
    return newId;
}

export function clearLLMConfigsFromCode() {
    llmConfigsFromCode.set([]);
}