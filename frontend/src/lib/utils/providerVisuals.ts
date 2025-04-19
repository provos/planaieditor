import { Cube, Cpu, GoogleLogo, Atom, Cloud, Globe, OpenAiLogo } from 'phosphor-svelte';
import type { Component } from 'svelte';
import type { LLMConfig } from '$lib/stores/llmConfigsStore'; // Import the type

// Define a mapping from provider names to icons and tailwind colors
interface ProviderVisuals {
    icon: Component;
    colorClass: string; // Tailwind CSS class for text color
}

export const providerVisualsMap: Record<LLMConfig['provider'], ProviderVisuals> = {
    openai: { icon: OpenAiLogo, colorClass: 'text-green-600' },
    anthropic: { icon: Atom, colorClass: 'text-orange-600' }, // Using Atom as a placeholder
    gemini: { icon: GoogleLogo, colorClass: 'text-blue-600' },
    ollama: { icon: Cpu, colorClass: 'text-purple-600' },
    remote_ollama: { icon: Cloud, colorClass: 'text-cyan-600' },
    openrouter: { icon: Globe, colorClass: 'text-rose-600' },
};

// Helper function to get visuals for a provider
export function getProviderVisuals(provider: LLMConfig['provider']): ProviderVisuals {
    return providerVisualsMap[provider] || { icon: Cube, colorClass: 'text-gray-500' }; // Default fallback
}