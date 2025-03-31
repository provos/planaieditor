<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { isValidPythonClassName } from '$lib/utils/validation';
	import FieldEditor from '../FieldEditor.svelte';

	type FieldType = 'string' | 'integer' | 'float' | 'list_string' | 'list_integer' | 'list_float';

	interface Field {
		name: string;
		type: FieldType;
		required: boolean;
		default?: any;
	}

	interface NodeData {
		className: string;
		fields: Field[];
	}

	let { id, data } = $props<{ id: string; data: NodeData }>();

	let classNameError = $state('');
	let showFieldEditor = $state(false);

	function updateClassName(e: Event) {
		const target = e.target as HTMLInputElement;
		const newClassName = target.value;

		if (!isValidPythonClassName(newClassName)) {
			classNameError = 'Invalid Python class name';
		} else {
			classNameError = '';
			data.className = newClassName;
		}
	}

	function addNewField(field: Field) {
		data.fields = [...data.fields, field];
		showFieldEditor = false;
	}

	function deleteField(index: number) {
		data.fields = data.fields.filter((_: Field, i: number) => i !== index);
	}
</script>

<div class="min-w-[250px] rounded-md border border-gray-300 bg-white p-4 shadow-md">
	<!-- Node handles -->
	<Handle type="source" position={Position.Bottom} id="output" />
	<Handle type="target" position={Position.Top} id="input" />

	<!-- Node header -->
	<div class="mb-3 border-b border-gray-200 pb-2">
		<div class="text-sm font-semibold text-gray-500">Task Definition</div>
		<div class="flex flex-col">
			<label class="text-xs text-gray-500">Class Name:</label>
			<input
				type="text"
				value={data.className}
				on:input={updateClassName}
				class="rounded border border-gray-300 px-2 py-1 text-sm {classNameError
					? 'border-red-500'
					: ''}"
			/>
			{#if classNameError}
				<div class="mt-1 text-xs text-red-500">{classNameError}</div>
			{/if}
		</div>
	</div>

	<!-- Field list -->
	<div class="mb-3">
		<div class="mb-2 flex items-center justify-between">
			<div class="text-sm font-semibold">Fields</div>
			<button
				class="rounded bg-blue-500 px-2 py-1 text-xs text-white transition-colors hover:bg-blue-600"
				on:click={() => (showFieldEditor = true)}
			>
				Add Field
			</button>
		</div>

		{#if data.fields.length === 0}
			<div class="text-sm italic text-gray-500">No fields defined</div>
		{:else}
			<div class="space-y-2">
				{#each data.fields as field, index}
					<div
						class="flex items-center justify-between rounded border border-gray-200 bg-gray-50 p-2"
					>
						<div>
							<div class="text-sm font-medium">{field.name}</div>
							<div class="text-xs text-gray-500">
								{field.type}{field.required ? '' : ' (optional)'}
							</div>
						</div>
						<button
							class="text-xs text-red-500 hover:text-red-700"
							on:click={() => deleteField(index)}
						>
							✕
						</button>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Field editor modal -->
	{#if showFieldEditor}
		<div class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30">
			<div class="w-full max-w-md rounded-lg bg-white p-4">
				<FieldEditor
					on:save={(e) => addNewField(e.detail)}
					on:cancel={() => (showFieldEditor = false)}
					existingFieldNames={data.fields.map((f: Field) => f.name)}
				/>
			</div>
		</div>
	{/if}
</div>
