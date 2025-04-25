import * as monaco from 'monaco-editor';

// This file now only imports and exports the main monaco library object.
// The worker environment setup has been moved to the main page component (+page.svelte)
// to ensure it runs only once per page load.

export default monaco;