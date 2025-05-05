import { setupMonacoEnvironment } from '$lib/monaco';
import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';
import { LspManager } from '$lib/lsp/lspManager';
import { socketStore } from './socketStore.svelte';

/**
 * Reactive state holding the Monaco Editor API instance.
 * It's initialized to null and populated by initializeMonaco.
 */
export let monacoInstance = $state({
    instance: null as typeof Monaco | null,
});

let lspManagerInstance: LspManager | null = null;

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

/**
 * Starts the LSP Manager if Monaco and Socket are ready.
 * Call this function after the socket connection is established.
 */
export async function startLspManager(): Promise<boolean> {
    // Ensure we have Monaco instance and Socket before starting
    if (!monacoInstance.instance) {
        console.error('[LSP Manager] Cannot start LSP Manager: Monaco instance not available');
        return false;
    }

    if (!socketStore.socket || !socketStore.isConnected) {
        console.error('[LSP Manager] Cannot start LSP Manager: Socket not connected');
        return false;
    }

    // If we already have an LSP manager instance, stop it first
    if (lspManagerInstance) {
        console.log('[LSP Manager] Stopping existing LSP Manager before creating a new one');
        await stopLspManager();
    }

    console.log('[LSP Manager] Creating new LSP Manager instance');
    lspManagerInstance = new LspManager(socketStore.socket, monacoInstance.instance);

    try {
        console.log('[LSP Manager] Starting LSP Manager');
        await lspManagerInstance.start();
        console.log('[LSP Manager] LSP Manager started successfully');
    } catch (error) {
        console.error('[LSP Manager] Failed to start LSP Manager:', error);
        lspManagerInstance = null;
    }

    return lspManagerInstance !== null;
}

/**
 * Stops the LSP Manager.
 * Call this function when the socket disconnects or when unmounting the application.
 */
export async function stopLspManager(): Promise<void> {
    if (!lspManagerInstance) {
        console.log('[LSP Manager] No LSP Manager instance to stop');
        return;
    }

    try {
        console.log('[LSP Manager] Stopping LSP Manager');
        await lspManagerInstance.stop();
        console.log('[LSP Manager] LSP Manager stopped successfully');
    } catch (error) {
        console.error('[LSP Manager] Error stopping LSP Manager:', error);
    } finally {
        lspManagerInstance = null;
    }
}