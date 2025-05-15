export function escapeHtml(text: string): string {
	return text
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#039;');
}

export function formatErrorMessage(errorText: string): string {
	if (!errorText) return '';

	// First escape HTML special characters to prevent XSS
	const escaped = escapeHtml(errorText);

	// Then replace newlines with <br> tags
	return escaped.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');
}

// Debounce function to prevent excessive calls to the server
export function debounce(func: Function, wait: number) {
	let timeout: number | undefined;
	return function executedFunction(...args: any[]) {
		const later = () => {
			clearTimeout(timeout);
			func(...args);
		};
		clearTimeout(timeout);
		timeout = setTimeout(later, wait);
	};
}

// A debounce functiont that creates a timeout for each ID passed into the function
export function debounceWithID(func: (...args: any[]) => void, wait: number) {
	const timeouts = new Map<string, number>(); // Stores timeout IDs for each unique id

	// The returned function now takes the same arguments as the original 'func'.
	// The first argument is assumed to be the ID for debouncing.
	return function (...args: any[]) {
		if (args.length === 0 || typeof args[0] !== 'string') {
			console.error(
				'debounceWithID: First argument must be a string ID to be used as a key. Debouncing skipped for this call.'
			);
			// Optionally, you could call func(...args) here if you want non-debounced execution for invalid keys,
			// but typically, if the keying mechanism fails, you might want to prevent execution or log more actively.
			return;
		}
		const idForDebounceKey = args[0] as string;

		const later = () => {
			timeouts.delete(idForDebounceKey); // Clean up the timeout from the map once executed
			func(...args); // Execute the original function with all its arguments
		};

		// Clear any existing timeout for this specific ID
		const existingTimeout = timeouts.get(idForDebounceKey);
		if (existingTimeout) {
			clearTimeout(existingTimeout);
		}

		// Set a new timeout for this specific ID
		timeouts.set(idForDebounceKey, setTimeout(later, wait));
	};
}

export function downloadFile(filename: string = 'planai-graph.json', content: string) {
	const blob = new Blob([content], { type: 'application/json' });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);
}

// Helper to generate unique node names
export function generateUniqueName(baseName: string, existingNames: Set<string>): string {
	let counter = 1;
	let uniqueName = `${baseName}${counter}`;
	while (existingNames.has(uniqueName)) {
		counter++;
		uniqueName = `${baseName}${counter}`;
	}
	return uniqueName;
}
