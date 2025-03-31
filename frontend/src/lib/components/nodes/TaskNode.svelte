<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { isValidPythonClassName, isValidPythonIdentifier } from '$lib/utils/validation';

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

	// State variables
	let classNameError = $state('');
	let editingNewField = $state(false);
	let newFieldName = $state('');
	let newFieldType = $state<FieldType>('string');
	let newFieldRequired = $state(true);
	let newFieldNameError = $state('');

	// Field type options
	const FIELD_TYPE_OPTIONS: Record<FieldType, string> = {
		string: 'String',
		integer: 'Integer',
		float: 'Float',
		list_string: 'List[str]',
		list_integer: 'List[int]',
		list_float: 'List[float]'
	};

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

	function validateNewFieldName() {
		if (!newFieldName) {
			newFieldNameError = 'Required';
			return false;
		}

		if (!isValidPythonIdentifier(newFieldName)) {
			newFieldNameError = 'Invalid Python identifier';
			return false;
		}

		if (data.fields.some((f: Field) => f.name === newFieldName)) {
			newFieldNameError = 'Name exists';
			return false;
		}

		newFieldNameError = '';
		return true;
	}

	function addField() {
		if (!validateNewFieldName()) return;

		data.fields = [
			...data.fields,
			{
				name: newFieldName,
				type: newFieldType,
				required: newFieldRequired
			}
		];

		// Reset form
		newFieldName = '';
		newFieldType = 'string';
		newFieldRequired = true;
		editingNewField = false;
	}

	function deleteField(index: number) {
		data.fields = data.fields.filter((_: Field, i: number) => i !== index);
	}

	function cancelNewField() {
		newFieldName = '';
		newFieldNameError = '';
		editingNewField = false;
	}
</script>

<div class="task-node w-56 rounded-md border border-gray-300 bg-white shadow-md">
	<!-- Node handles -->
	<Handle type="source" position={Position.Bottom} id="output" />
	<Handle type="target" position={Position.Top} id="input" />

	<!-- Header with class name -->
	<div class="border-b border-gray-200 bg-gray-50 p-2">
		<label class="block text-xs font-medium text-gray-500">Class Name:</label>
		<input
			type="text"
			value={data.className}
			onblur={updateClassName}
			class="w-full border border-gray-200 bg-white px-1 py-0.5 text-sm {classNameError
				? 'border-red-500'
				: ''}"
		/>
		{#if classNameError}
			<div class="mt-0.5 text-xs text-red-500">{classNameError}</div>
		{/if}
	</div>

	<!-- Fields list -->
	<div class="max-h-48 overflow-y-auto p-2">
		<div class="mb-1 flex items-center justify-between">
			<div class="text-xs font-semibold text-gray-500">Fields</div>
			{#if !editingNewField}
				<button
					class="rounded px-1.5 py-0.5 text-xs text-blue-500 hover:bg-blue-50"
					onclick={() => (editingNewField = true)}
				>
					+ Add
				</button>
			{/if}
		</div>

		{#if data.fields.length === 0 && !editingNewField}
			<div class="py-1 text-xs italic text-gray-400">No fields defined</div>
		{/if}

		<!-- Existing fields -->
		{#if data.fields.length > 0}
			<div class="space-y-1.5">
				{#each data.fields as field, index}
					<div class="flex items-center justify-between rounded bg-gray-50 px-1.5 py-1">
						<div class="flex flex-col">
							<div class="text-xs font-medium">{field.name}</div>
							<div class="text-xs text-gray-500">
								{FIELD_TYPE_OPTIONS[field.type as FieldType]}{field.required ? '' : ' (optional)'}
							</div>
						</div>
						<button
							class="h-5 w-5 rounded-full text-xs text-red-400 hover:bg-red-50 hover:text-red-500"
							onclick={() => deleteField(index)}
						>
							✕
						</button>
					</div>
				{/each}
			</div>
		{/if}

		<!-- New field form -->
		{#if editingNewField}
			<div class="mt-2 rounded border border-gray-200 bg-gray-50 p-1.5">
				<div class="mb-1.5">
					<input
						type="text"
						bind:value={newFieldName}
						onblur={validateNewFieldName}
						placeholder="Field name"
						class="w-full rounded border border-gray-200 px-1.5 py-0.5 text-xs {newFieldNameError
							? 'border-red-500'
							: ''}"
					/>
					{#if newFieldNameError}
						<div class="mt-0.5 text-xs text-red-500">{newFieldNameError}</div>
					{/if}
				</div>

				<div class="mb-1.5 flex items-center">
					<select
						bind:value={newFieldType}
						class="w-full rounded border border-gray-200 px-1 py-0.5 text-xs"
					>
						{#each Object.entries(FIELD_TYPE_OPTIONS) as [value, label]}
							<option {value}>{label}</option>
						{/each}
					</select>
				</div>

				<div class="mb-1.5 flex items-center text-xs">
					<input
						type="checkbox"
						id="newFieldRequired"
						bind:checked={newFieldRequired}
						class="h-3 w-3 rounded"
					/>
					<label for="newFieldRequired" class="ml-1 text-xs">Required</label>
				</div>

				<div class="flex justify-end space-x-1">
					<button
						class="rounded bg-gray-200 px-1.5 py-0.5 text-xs hover:bg-gray-300"
						onclick={cancelNewField}
					>
						Cancel
					</button>
					<button
						class="rounded bg-blue-500 px-1.5 py-0.5 text-xs text-white hover:bg-blue-600"
						onclick={addField}
					>
						Add
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>
