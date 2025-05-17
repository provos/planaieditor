import { backendUrl } from '$lib/utils/backendUrl';

// Define Item type for API responses
export type FilesystemItem = {
	name: string;
	type: 'file' | 'directory';
	path: string;
};

export type ListDirectoryResponse = {
	path: string;
	items: FilesystemItem[];
};

/**
 * Reads the content of a file from the backend.
 *
 * @param path - The relative path to the file on the server (e.g., "/data/my_file.txt").
 * @returns A Promise resolving to a Blob containing the file content.
 * @throws An error with a message if the request fails or the path is invalid.
 */
export async function readFile(path: string): Promise<Blob> {
	if (!path || typeof path !== 'string') {
		throw new Error('readFile: Invalid path provided.');
	}

	const url = `${backendUrl}/api/filesystem/read?path=${encodeURIComponent(path)}`;
	console.debug(`Reading file from: ${url}`); // Optional debug log

	try {
		const response = await fetch(url, {
			method: 'GET'
		});

		if (!response.ok) {
			let errorMessage = `Failed to read file: ${response.status} ${response.statusText}`;
			try {
				const errorData = await response.json();
				errorMessage = errorData.message || errorMessage;
			} catch (jsonError) {
				// Ignore if response wasn't JSON, use the status text
				console.error(`readFile error for path "${path}": ${errorMessage}`);
			}
			console.error(`readFile error for path "${path}": ${errorMessage}`);
			throw new Error(errorMessage);
		}

		// Return the file content as a Blob
		return await response.blob();
	} catch (error: any) {
		console.error(`readFile network error for path "${path}": ${error.message}`);
		// Re-throw the error after logging
		throw error;
	}
}

/**
 * Writes content to a file on the backend.
 *
 * @param path - The relative path where the file should be saved on the server (e.g., "/data/new_file.txt").
 * @param content - The string content to write to the file.
 * @returns A Promise resolving to an object containing a success message and the saved path.
 * @throws An error with a message if the request fails or the path/content is invalid.
 */
export async function writeFile(
	path: string,
	content: string
): Promise<{ message: string; path: string }> {
	if (!path || typeof path !== 'string') {
		throw new Error('writeFile: Invalid path provided.');
	}
	if (typeof content !== 'string') {
		// Allow empty string, but not other types
		throw new Error('writeFile: Invalid content provided (must be a string).');
	}

	const url = `${backendUrl}/api/filesystem/write`;
	console.debug(`Writing file to: ${url} with path: ${path}`); // Optional debug log

	try {
		const response = await fetch(url, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ path, content })
		});

		const responseData = await response.json(); // Attempt to parse JSON regardless of status

		if (!response.ok) {
			const errorMessage =
				responseData.message || `Failed to write file: ${response.status} ${response.statusText}`;
			console.error(`writeFile error for path "${path}": ${errorMessage}`);
			throw new Error(errorMessage);
		}

		// Expecting { message: string, path: string } on success
		if (
			!responseData ||
			typeof responseData.message !== 'string' ||
			typeof responseData.path !== 'string'
		) {
			throw new Error('writeFile: Invalid success response format from server.');
		}

		console.info(`Successfully wrote file: ${responseData.path}`);
		return responseData;
	} catch (error: any) {
		// If it's not an error we already created, log it as a network error
		if (!(error instanceof Error && error.message.startsWith('Failed to write file:'))) {
			console.error(`writeFile network error for path "${path}": ${error.message}`);
		}
		// Re-throw the error
		throw error;
	}
}

/**
 * Helper to read a file assumed to be text.
 *
 * @param path - The relative path to the text file on the server.
 * @returns A Promise resolving to the string content of the file.
 * @throws An error if reading fails or the content cannot be decoded as text.
 */
export async function readTextFile(path: string): Promise<string> {
	const blob = await readFile(path);
	try {
		return await blob.text();
	} catch (error: any) {
		console.error(`readTextFile error decoding blob for path "${path}": ${error.message}`);
		throw new Error(`Failed to decode file content as text for path: ${path}`);
	}
}

/**
 * Lists the contents of a directory on the backend.
 *
 * @param path - The relative path to the directory on the server (e.g., "/" or "/data/subdir").
 * @returns A Promise resolving to an object containing the canonical path and a list of items.
 * @throws An error with a message if the request fails or the path is invalid.
 */
export async function listDirectory(path: string): Promise<ListDirectoryResponse> {
	if (typeof path !== 'string') {
		// Allow empty string for root potentially, backend handles logic
		throw new Error('listDirectory: Invalid path provided.');
	}

	// Ensure the path starts reasonably for the backend logic that expects relative paths
	const requestPath = path === '/' ? '/' : path.replace(/^\//, ''); // Use '/' for root, strip leading slash otherwise

	const url = `${backendUrl}/api/filesystem/list?path=${encodeURIComponent(requestPath)}`;
	console.debug(`Listing directory from: ${url}`); // Optional debug log

	try {
		const response = await fetch(url, {
			method: 'GET'
		});

		const responseData = await response.json(); // Attempt to parse JSON regardless of status

		if (!response.ok) {
			const errorMessage =
				responseData.message ||
				`Failed to list directory: ${response.status} ${response.statusText}`;
			console.error(`listDirectory error for path "${requestPath}": ${errorMessage}`);
			throw new Error(errorMessage);
		}

		// Validate the expected response structure
		if (
			!responseData ||
			typeof responseData.path !== 'string' ||
			!Array.isArray(responseData.items)
		) {
			console.error('listDirectory: Invalid response format from server.', responseData);
			throw new Error('listDirectory: Invalid response format from server.');
		}

		// Further validation of item structure could be added here if needed

		console.debug(`Successfully listed directory: ${responseData.path}`);
		return responseData as ListDirectoryResponse; // Type assertion after validation
	} catch (error: any) {
		// If it's not an error we already created, log it as a network error
		if (
			!(
				error instanceof Error &&
				(error.message.startsWith('Failed to list directory:') ||
					error.message.startsWith('listDirectory:'))
			)
		) {
			console.error(`listDirectory network error for path "${requestPath}": ${error.message}`);
		}
		// Re-throw the error
		throw error;
	}
}
