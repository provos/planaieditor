import * as monaco from 'monaco-editor';

// Import the workers in a production-safe way
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import cssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker';
import htmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker';
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker';

/**
 * Sets up the Monaco environment with web workers
 * Call this function once in the app's lifecycle (e.g., in the main page component's onMount)
 * to ensure the Monaco editor can utilize web workers for various language features.
 *
 * @returns {boolean} True if setup was successful, false if not in a browser environment
 */
export function setupMonacoEnvironment(): boolean {
    // Only run in browser environments
    if (typeof window === 'undefined') {
        return false;
    }

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

    return true;
}

// Export monaco as the default export for backward compatibility
export default monaco;