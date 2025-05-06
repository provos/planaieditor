// Import the workers in a production-safe way
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import cssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker';
import htmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker';
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker';
import type * as Monaco from 'monaco-editor/esm/vs/editor/editor.api';

import 'monaco-editor/esm/vs/language/typescript/monaco.contribution';
import 'monaco-editor/esm/vs/language/css/monaco.contribution';
import 'monaco-editor/esm/vs/language/json/monaco.contribution';
import 'monaco-editor/esm/vs/language/html/monaco.contribution';


/**
 * Dynamically imports Monaco and sets up the Monaco environment with web workers.
 * Call this function once in the app's lifecycle (e.g., in the main page component's onMount)
 * to ensure the Monaco editor can utilize web workers for various language features.
 *
 * @returns {Promise<typeof Monaco | null>} A promise resolving to the Monaco API object, or null if not in a browser environment.
 */
export async function setupMonacoEnvironment(): Promise<typeof Monaco | null> {
    // Only run in browser environments
    if (typeof window === 'undefined') {
        console.warn('Monaco Environment setup skipped: Not in a browser environment.');
        return null;
    }

    // Dynamically import Monaco only on the client-side
    const monaco = await import('monaco-editor');

    // Set up the MonacoEnvironment global
    (self as any).MonacoEnvironment = {
        getWorker: function (_: string, label: string) {
            switch (label) {
                case 'json':
                    return new jsonWorker();
                case 'css':
                case 'scss':
                case 'less':
                    return new cssWorker();
                case 'html':
                case 'handlebars':
                case 'razor':
                    return new htmlWorker();
                case 'typescript':
                case 'javascript':
                    return new tsWorker();
                default:
                    return new editorWorker();
            }
        }
    };

    // Initialize the services
    console.log('Initializing VSCode services...');
    const { initServices } = await import('monaco-languageclient/vscode/services');

    const getTextmateServiceOverride = await import('@codingame/monaco-vscode-textmate-service-override');
    const getThemeServiceOverride = await import('@codingame/monaco-vscode-theme-service-override');
    const getLanguagesServiceOverride = await import('@codingame/monaco-vscode-languages-service-override');
    await import('@codingame/monaco-vscode-theme-defaults-default-extension');
    await import('@codingame/monaco-vscode-json-default-extension');
    await import('@codingame/monaco-vscode-python-default-extension');

    await initServices({
        loadThemes: true,
        serviceOverrides: {
            ...getTextmateServiceOverride.default(),
            ...getThemeServiceOverride.default(),
            ...getLanguagesServiceOverride.default(),
        },
    });

    monaco.languages.register({
        id: 'python',
        extensions: ['.py'],
        aliases: ['Python', 'python'],
        mimetypes: ['text/x-python'],
    });
    console.log('Monaco Environment setup complete.');
    return monaco; // Return the dynamically imported monaco object
}