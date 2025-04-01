<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';
	import ArrowsIn from 'phosphor-svelte/lib/ArrowsIn';

	// Extend the base data interface
	interface JoinedWorkerData extends BaseWorkerData {
		joinMethod: 'merge' | 'zip' | 'custom';
	}

	let { id, data } = $props<{
		id: string;
		data: JoinedWorkerData;
	}>();

	// Ensure additional fields are initialized
	if (!data.joinMethod) {
		data.joinMethod = 'merge';
	}

	// Join method state
	let joinMethod = $state(data.joinMethod);

	// Simplified handleCodeUpdate for the new component
	function handleCodeUpdate(newCode: string) {
		data.consumeWork = newCode;
	}

	// Join method handling
	function updateJoinMethod(method: 'merge' | 'zip' | 'custom') {
		data.joinMethod = method;
		joinMethod = method;
	}

	// Update join method when data changes
	$effect(() => {
		joinMethod = data.joinMethod;
	});
</script>

<BaseWorkerNode {id} {data} defaultName="JoinedTaskWorker" minHeight={200}>
	<!-- Join Method Section -->
	<div class="mb-2 flex-none">
		<div class="flex items-center justify-between">
			<h3 class="text-2xs font-semibold text-gray-600">Join Method</h3>
			<div
				class="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-blue-100 text-blue-500 shadow-sm"
			>
				<ArrowsIn size={8} weight="bold" />
			</div>
		</div>

		<div class="mt-1 grid grid-cols-3 gap-1">
			<button
				class="text-2xs rounded border px-2 py-0.5 {joinMethod === 'merge'
					? 'border-blue-500 bg-blue-50 text-blue-700'
					: 'border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100'}"
				onclick={() => updateJoinMethod('merge')}
			>
				Merge
			</button>
			<button
				class="text-2xs rounded border px-2 py-0.5 {joinMethod === 'zip'
					? 'border-blue-500 bg-blue-50 text-blue-700'
					: 'border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100'}"
				onclick={() => updateJoinMethod('zip')}
			>
				Zip
			</button>
			<button
				class="text-2xs rounded border px-2 py-0.5 {joinMethod === 'custom'
					? 'border-blue-500 bg-blue-50 text-blue-700'
					: 'border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100'}"
				onclick={() => updateJoinMethod('custom')}
			>
				Custom
			</button>
		</div>
	</div>

	<!-- Code Section (only shown when join method is 'custom') -->
	{#if joinMethod === 'custom'}
		<div class="flex min-h-0 flex-grow flex-col overflow-hidden">
			<EditableCodeSection
				title="consume_work()"
				code={data.consumeWork}
				language="python"
				onUpdate={handleCodeUpdate}
			/>
		</div>
	{/if}
</BaseWorkerNode>

<style>
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
