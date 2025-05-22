/*
 * This is a modified version of the persistedState function
 * from https://github.com/oMaN-Rod/svelte-persisted-state
 *
 * The original code was released under this license:
 * Copyright (c) 2024 O.
 *
 * Permission is hereby granted, free of charge, to any person
 * obtaining a copy of this software and associated documentation
 * files (the "Software"), to deal in the Software without
 * restriction, including without limitation the rights to use,
 * copy, modify, merge, publish, distribute, sublicense, and/or
 * sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following
 * conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 * OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 * WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OF IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 *
 * The code was modified to make the persisted store completely transparent to the developer.
 */
type Serializer<T> = {
	parse: (text: string) => T;
	stringify: (object: T) => string;
};

type StorageType = 'local' | 'session';

interface Options<T> {
	storage?: StorageType;
	serializer?: Serializer<T>;
	syncTabs?: boolean;
	onWriteError?: (error: unknown) => void;
	onParseError?: (error: unknown) => void;
	beforeRead?: (value: T) => T;
	beforeWrite?: (value: T) => T;
}

function getStorage(type: StorageType) {
	return type === 'local' ? localStorage : sessionStorage;
}

export function persistedState<T>(key: string, initialValue: T, options: Options<T> = {}) {
	const {
		storage = 'local',
		serializer = JSON,
		syncTabs = true,
		onWriteError = console.error,
		onParseError = console.error,
		beforeRead = (v: T) => v,
		beforeWrite = (v: T) => v
	} = options;

	const browser = typeof window !== 'undefined' && typeof document !== 'undefined';
	const storageArea = browser ? getStorage(storage) : null;

	let currentInitialValue = initialValue;

	// Initial read from storage (synchronous)
	if (browser && storageArea) {
		try {
			const item = storageArea.getItem(key);
			if (item !== null) {
				currentInitialValue = beforeRead(serializer.parse(item));
			}
		} catch (error) {
			onParseError(error);
			// If parsing fails, currentInitialValue remains the original initialValue
		}
	}

	let state = $state(currentInitialValue);

	// Reactive persistence and synchronization logic
	if (browser && storageArea) {
		$effect.root(() => {
			// Establish a root reactive scope for effects
			// Effect to write to storage when state changes
			$effect(() => {
				const valueToStore = beforeWrite(state);
				try {
					storageArea.setItem(key, serializer.stringify(valueToStore));
				} catch (error) {
					onWriteError(error);
				}
			});

			// Effect for tab synchronization
			if (syncTabs && storage === 'local' && window) {
				// Ensure window exists
				const handleStorageEvent = (event: StorageEvent) => {
					if (event.key === key && event.storageArea === storageArea) {
						let newValueFromStorage: T;
						if (event.newValue === null) {
							// Item removed from storage, reset to initialValue after beforeRead
							newValueFromStorage = beforeRead(initialValue);
						} else {
							try {
								const deserializedNewValue = serializer.parse(event.newValue);
								newValueFromStorage = beforeRead(deserializedNewValue);
							} catch (error) {
								onParseError(error);
								return; // Don't update state if parsing failed
							}
						}

						// Only update if the value has actually changed to avoid unnecessary updates
						// and potential loops if beforeRead/serializer are not perfectly symmetric.
						if (JSON.stringify(state) !== JSON.stringify(newValueFromStorage)) {
							state = newValueFromStorage;
						}
					}
				};
				window.addEventListener('storage', handleStorageEvent);

				// Cleanup function for the root effect: remove the event listener
				return () => {
					window.removeEventListener('storage', handleStorageEvent);
				};
			}
			return () => {}; // Default cleanup if syncTabs is off or not applicable
		});
	}

	return state; // Return the raw $state variable
}
