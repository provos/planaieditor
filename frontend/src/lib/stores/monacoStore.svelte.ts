import { setupMonacoEnvironment } from '$lib/monaco';
import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';

/**
 * Reactive state holding the Monaco Editor API instance.
 * It's initialized to null and populated by initializeMonaco.
 */
export let monacoInstance = $state({
    instance: null as typeof Monaco | null,
});

/**
 * Flag to prevent multiple initialization attempts.
 */
let isInitializing = false;
let isInitialized = false;

/**
 * Initializes the Monaco environment exactly once.
 * Call this function early in the application lifecycle (e.g., root layout's onMount).
 */
export async function initializeMonaco(): Promise<void> {
    // Run only in browser and only if not already initialized or initializing
    if (typeof window === 'undefined' || isInitialized || isInitializing) {
        if (isInitialized) console.log('Monaco already initialized.');
        if (isInitializing) console.log('Monaco initialization already in progress.');
        return;
    }

    console.log('Attempting to initialize Monaco environment...');
    isInitializing = true;

    try {
        const instance = await setupMonacoEnvironment();
        if (instance) {
            monacoInstance.instance = instance;
            isInitialized = true;
            console.log('Monaco instance obtained successfully.');
        } else {
            console.error('Failed to obtain Monaco instance from setup function.');
        }
    } catch (error) {
        console.error('Error during Monaco initialization:', error);
    } finally {
        isInitializing = false;
    }
}