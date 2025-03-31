<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { isValidPythonIdentifier } from '$lib/utils/validation';

	type FieldType = 'string' | 'integer' | 'float' | 'list_string' | 'list_integer' | 'list_float';

	interface Field {
		name: string;
		type: FieldType;
		required: boolean;
		default?: any;
	}

	let { existingFieldNames = [] } = $props<{ existingFieldNames?: string[] }>();

	const FIELD_TYPE_LABELS = {
		string: 'String',
		integer: 'Integer',
		float: 'Float',
		list_string: 'List of strings',
		list_integer: 'List of integers',
		list_float: 'List of floats'
	};

	const dispatch = createEventDispatcher<{
		save: Field;
		cancel: void;
	}>();

	let fieldName = $state('');
	let fieldType = $state<FieldType>('string');
	let required = $state(true);
	let defaultValue = $state('');
	let fieldNameError = $state('');
	let defaultValueError = $state('');

	function validateFieldName() {
		if (!fieldName) {
			fieldNameError = 'Field name is required';
			return false;
		}

		if (!isValidPythonIdentifier(fieldName)) {
			fieldNameError = 'Invalid Python identifier';
			return false;
		}

		if (existingFieldNames.includes(fieldName)) {
			fieldNameError = 'Field name already exists';
			return false;
		}

		fieldNameError = '';
		return true;
	}

	function validateDefaultValue() {
		if (!defaultValue) {
			defaultValueError = '';
			return true;
		}

		try {
			switch (fieldType) {
				case 'integer':
					if (!/^-?\d+$/.test(defaultValue)) {
						throw new Error('Must be an integer');
					}
					break;
				case 'float':
					if (!/^-?\d+(\.\d+)?$/.test(defaultValue)) {
						throw new Error('Must be a float');
					}
					break;
				case 'list_string':
				case 'list_integer':
				case 'list_float':
					// Basic JSON array validation
					const parsed = JSON.parse(defaultValue);
					if (!Array.isArray(parsed)) {
						throw new Error('Must be a JSON array');
					}
					break;
			}
			defaultValueError = '';
			return true;
		} catch (error) {
			defaultValueError = error instanceof Error ? error.message : 'Invalid value';
			return false;
		}
	}

	function saveField() {
		const isValidName = validateFieldName();
		const isValidDefault = validateDefaultValue();

		if (!isValidName || !isValidDefault) {
			return;
		}

		// Process the default value based on type
		let processedDefault: any = defaultValue;
		if (defaultValue) {
			switch (fieldType) {
				case 'integer':
					processedDefault = parseInt(defaultValue);
					break;
				case 'float':
					processedDefault = parseFloat(defaultValue);
					break;
				case 'list_string':
				case 'list_integer':
				case 'list_float':
					processedDefault = JSON.parse(defaultValue);
					break;
			}
		}

		dispatch('save', {
			name: fieldName,
			type: fieldType,
			required,
			default: defaultValue ? processedDefault : undefined
		});
	}

	function cancel() {
		dispatch('cancel');
	}
</script>

<div class="field-editor">
	<h3 class="mb-4 text-lg font-semibold">Add Field</h3>

	<!-- Field Name -->
	<div class="mb-3">
		<label class="mb-1 block text-sm font-medium text-gray-700">Field Name</label>
		<input
			type="text"
			bind:value={fieldName}
			on:blur={validateFieldName}
			class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm {fieldNameError
				? 'border-red-500'
				: ''}"
			placeholder="field_name"
		/>
		{#if fieldNameError}
			<div class="mt-1 text-xs text-red-500">{fieldNameError}</div>
		{/if}
	</div>

	<!-- Field Type -->
	<div class="mb-3">
		<label class="mb-1 block text-sm font-medium text-gray-700">Field Type</label>
		<select
			bind:value={fieldType}
			class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
		>
			{#each Object.entries(FIELD_TYPE_LABELS) as [value, label]}
				<option {value}>{label}</option>
			{/each}
		</select>
	</div>

	<!-- Required -->
	<div class="mb-3 flex items-center">
		<input
			type="checkbox"
			id="required"
			bind:checked={required}
			class="h-4 w-4 rounded text-blue-600"
		/>
		<label for="required" class="ml-2 text-sm font-medium text-gray-700">Required field</label>
	</div>

	<!-- Default Value -->
	<div class="mb-4">
		<label class="mb-1 block text-sm font-medium text-gray-700">
			Default Value {required ? '(optional)' : '(required)'}
		</label>
		<input
			type="text"
			bind:value={defaultValue}
			on:blur={validateDefaultValue}
			class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm {defaultValueError
				? 'border-red-500'
				: ''}"
			placeholder={fieldType === 'string'
				? '"default value"'
				: fieldType === 'integer'
					? '42'
					: fieldType === 'float'
						? '3.14'
						: '["item1", "item2"]'}
		/>
		{#if defaultValueError}
			<div class="mt-1 text-xs text-red-500">{defaultValueError}</div>
		{/if}
		<div class="mt-1 text-xs text-gray-500">
			{#if fieldType === 'list_string' || fieldType === 'list_integer' || fieldType === 'list_float'}
				Enter as JSON array: e.g. ["value1", "value2"] or [1, 2, 3]
			{/if}
		</div>
	</div>

	<!-- Buttons -->
	<div class="flex justify-end space-x-2">
		<button
			class="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
			on:click={cancel}
		>
			Cancel
		</button>
		<button
			class="rounded-md border border-transparent bg-blue-500 px-3 py-2 text-sm text-white hover:bg-blue-600"
			on:click={saveField}
		>
			Add Field
		</button>
	</div>
</div>
