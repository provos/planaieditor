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

export function arraysEqual(arr1: any[], arr2: any[]): boolean {
	if (arr1.length !== arr2.length) {
		return false; // Arrays of different lengths cannot be equal
	}
	for (let i = 0; i < arr1.length; i++) {
		if (arr1[i] !== arr2[i]) {
			return false; // Found a differing element
		}
	}
	return true; // All elements matched
}
