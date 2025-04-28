<script lang="ts">
	import { backendUrl } from '$lib/utils/backendUrl';
	import { onMount } from 'svelte';
	import GearSix from 'phosphor-svelte/lib/GearSix';
	import Database from 'phosphor-svelte/lib/Database';
	import X from 'phosphor-svelte/lib/X';
	import Check from 'phosphor-svelte/lib/Check';
	import { selectedInterpreterPath } from '$lib/stores/pythonInterpreterStore.svelte';

	// Interpreter data structure
	interface PythonEnvironment {
		path: string;
		name: string;
	}

	// Props
	// let { socket } = $props<{ socket: Socket | null }>(); // Removed socket prop

	// Component state
	let environments = $state<PythonEnvironment[]>([]);
	// let selectedPath = $state<string | null>(null); // Removed local state, using store now
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let isOpen = $state(false);

	// Fetch available interpreters
	async function fetchEnvironments() {
		isLoading = true;
		error = null;
		try {
			const response = await fetch(`${backendUrl}/api/venvs`);
			const data = await response.json();

			if (data.success) {
				environments = data.environments;
			} else {
				error = data.error || 'Failed to fetch Python environments';
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Network error';
			console.error('Error fetching Python environments:', err);
		} finally {
			isLoading = false;
		}
	}

	// Fetch current interpreter
	async function fetchCurrentInterpreter() {
		try {
			const response = await fetch(`${backendUrl}/api/current-venv`);
			const data = await response.json();

			if (data.success && data.path) {
				// selectedPath = data.path; // Update store instead
				selectedInterpreterPath.value = data.path;
			}
		} catch (err) {
			console.error('Error fetching current interpreter:', err);
		}
	}

	// Select an interpreter
	async function selectInterpreter(path: string) {
		try {
			const response = await fetch(`${backendUrl}/api/set-venv`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ path })
			});

			const data = await response.json();

			if (data.success) {
				// selectedPath = path; // Update store instead
				selectedInterpreterPath.value = path;
				error = null;
				isOpen = false; // Close the dropdown after selection
			} else {
				error = data.error || 'Failed to set Python interpreter';
				// selectedPath = null; // Update store instead
				selectedInterpreterPath.value = null;
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Network error';
			console.error('Error setting Python interpreter:', err);
		}
	}

	// Toggle dropdown
	function toggleDropdown() {
		isOpen = !isOpen;

		// Refresh environments list when opening
		if (isOpen && environments.length === 0) {
			fetchEnvironments();
		}
	}

	// Close dropdown if clicked outside
	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		const dropdown = document.getElementById('interpreter-dropdown');
		const button = document.getElementById('interpreter-button');

		if (isOpen && dropdown && button && !dropdown.contains(target) && !button.contains(target)) {
			isOpen = false;
		}
	}

	// Setup on component mount
	onMount(() => {
		fetchCurrentInterpreter();
		document.addEventListener('click', handleClickOutside);

		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});
</script>

<div class="relative inline-block text-left">
	<!-- Selector Button -->
	<button
		id="interpreter-button"
		type="button"
		class="inline-flex items-center justify-center gap-x-1.5 rounded-md bg-white px-3 py-1.5 text-xs font-medium text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
		class:ring-red-300={error}
		class:ring-yellow-300={!selectedInterpreterPath.value}
		class:bg-yellow-50={!selectedInterpreterPath.value}
		onclick={toggleDropdown}
	>
		<span class={!selectedInterpreterPath.value ? 'text-yellow-600' : 'text-gray-500'}>
			<Database class="h-4 w-4" />
		</span>
		{#if selectedInterpreterPath.value}
			<span class="max-w-[150px] truncate">
				{environments.find((env) => env.path === selectedInterpreterPath.value)?.name ||
					selectedInterpreterPath.value}
			</span>
		{:else}
			<span class="text-yellow-700">Select Python Interpreter</span>
		{/if}
	</button>

	<!-- Dropdown Menu -->
	{#if isOpen}
		<div
			id="interpreter-dropdown"
			class="absolute right-0 z-50 mt-2 w-96 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
		>
			<div class="p-2">
				<div class="mb-2 flex items-center justify-between border-b border-gray-100 pb-2">
					<h3 class="text-sm font-medium text-gray-900">Select Python Interpreter</h3>
					<button
						onclick={() => {
							isOpen = false;
						}}
						class="text-gray-400 hover:text-gray-600"
					>
						<X class="h-4 w-4" />
					</button>
				</div>

				{#if error}
					<div class="mb-2 rounded bg-red-50 p-2 text-sm text-red-600">
						{error}
					</div>
				{/if}

				{#if isLoading}
					<div class="px-1 py-2 text-sm text-gray-500">Loading interpreters...</div>
				{:else if environments.length === 0}
					<div class="px-1 py-2 text-sm text-gray-500">No Python interpreters found</div>
				{:else}
					<div class="max-h-64 overflow-y-auto">
						{#each environments as env (env.path)}
							<button
								class="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm hover:bg-gray-100"
								class:bg-blue-50={selectedInterpreterPath.value === env.path}
								onclick={() => selectInterpreter(env.path)}
							>
								<div class="flex-1 truncate">
									<div class="font-medium">{env.name}</div>
									<div class="truncate text-xs text-gray-500">{env.path}</div>
								</div>
								{#if selectedInterpreterPath.value === env.path}
									<Check class="h-4 w-4 text-blue-500" />
								{/if}
							</button>
						{/each}
					</div>
				{/if}

				<div class="mt-2 border-t border-gray-100 pt-2">
					<button
						onclick={fetchEnvironments}
						class="flex w-full items-center justify-center rounded-md bg-gray-50 px-3 py-2 text-sm font-medium text-gray-900 hover:bg-gray-100"
					>
						<GearSix class="mr-1.5 h-4 w-4 text-gray-500" />
						Refresh Interpreters
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
