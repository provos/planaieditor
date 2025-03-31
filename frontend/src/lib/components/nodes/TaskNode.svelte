<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { isValidPythonClassName, isValidPythonIdentifier } from '$lib/utils/validation';
	import { allClassNames } from '$lib/stores/classNameStore';

	type BaseFieldType = 'string' | 'integer' | 'float';
	type FieldType = BaseFieldType | `list_${BaseFieldType}`;

	interface Field {
		name: string;
		type: FieldType;
		required: boolean;
		default?: any;
	}

	interface NodeData {
		className: string;
		fields: Field[];
		nodeId: string; // The node's ID for validation
	}

	let { id, data } = $props<{
		id: string;
		data: NodeData;
	}>();

	// Ensure data.fields is initialized
	if (!data.fields) {
		data.fields = [];
	}

	// State variables
	let editingClassName = $state(false);
	let classNameError = $state('');
	let editingNewField = $state(false);
	let newFieldName = $state('');
	let newFieldType = $state<BaseFieldType>('string');
	let newFieldIsList = $state(false);
	let newFieldRequired = $state(true);
	let newFieldNameError = $state('');
	let tempClassName = $state(data.className);

	// Track current fields for rendering
	let currentFields = $state<Field[]>([...data.fields]);

	// Field type options
	const BASE_TYPE_LABELS = {
		string: 'str',
		integer: 'int',
		float: 'float'
	};

	function startEditingClassName() {
		tempClassName = data.className;
		editingClassName = true;
	}

	function validateClassName(name: string): boolean {
		// First check if it's a valid Python class name
		if (!isValidPythonClassName(name)) {
			classNameError = 'Invalid Python class name';
			return false;
		}

		// Then check if it's unique among all nodes
		let isDuplicate = false;
		const unsubscribe = allClassNames.subscribe((classMap: Map<string, string>) => {
			// Check all class names except this node's own
			classMap.forEach((className: string, nodeId: string) => {
				if (nodeId !== data.nodeId && className === name) {
					isDuplicate = true;
				}
			});
		});
		unsubscribe();

		if (isDuplicate) {
			classNameError = 'Class name already exists';
			return false;
		}

		classNameError = '';
		return true;
	}

	function updateClassName() {
		if (!validateClassName(tempClassName)) {
			return;
		}

		data.className = tempClassName;
		editingClassName = false;
	}

	function cancelEditingClassName() {
		tempClassName = data.className;
		classNameError = '';
		editingClassName = false;
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
			newFieldNameError = 'Field name exists';
			return false;
		}

		newFieldNameError = '';
		return true;
	}

	function getFullFieldType(): FieldType {
		return newFieldIsList ? (`list_${newFieldType}` as FieldType) : newFieldType;
	}

	function addField() {
		if (!validateNewFieldName()) return;

		const newField = {
			name: newFieldName,
			type: getFullFieldType(),
			required: newFieldRequired
		};

		// Add the field to data
		data.fields = [...data.fields, newField];

		// Update our local tracking state
		currentFields = [...data.fields];

		// Reset form
		newFieldName = '';
		newFieldType = 'string';
		newFieldIsList = false;
		newFieldRequired = true;
		editingNewField = false;
	}

	function deleteField(index: number) {
		data.fields = data.fields.filter((_: Field, i: number) => i !== index);
		currentFields = [...data.fields];
	}

	function cancelNewField() {
		newFieldName = '';
		newFieldNameError = '';
		editingNewField = false;
	}

	// Handle keydown for class name editing
	function handleClassNameKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			updateClassName();
		} else if (event.key === 'Escape') {
			cancelEditingClassName();
		}
	}

	// Format field type for display
	function formatFieldType(type: FieldType): string {
		if (type.startsWith('list_')) {
			const baseType = type.substring(5) as BaseFieldType;
			return `List[${BASE_TYPE_LABELS[baseType]}]`;
		}
		return BASE_TYPE_LABELS[type as BaseFieldType];
	}

	// Update local fields when data.fields changes
	$effect(() => {
		currentFields = [...data.fields];
	});
</script>

<div class="task-node w-52 rounded-md border border-gray-300 bg-white shadow-md">
	<!-- Node handles -->
	<Handle type="source" position={Position.Bottom} id="output" />
	<Handle type="target" position={Position.Top} id="input" />

	<!-- Header with editable class name -->
	<div class="border-b border-gray-200 bg-gray-50 p-1">
		{#if editingClassName}
			<div class="flex flex-col">
				<input
					type="text"
					bind:value={tempClassName}
					onblur={updateClassName}
					onkeydown={handleClassNameKeydown}
					class="w-full rounded border border-gray-200 bg-white px-1.5 py-0.5 text-xs font-medium {classNameError
						? 'border-red-500'
						: ''}"
					autofocus
				/>
				{#if classNameError}
					<div class="mt-0.5 text-xs text-red-500">{classNameError}</div>
				{/if}
			</div>
		{:else}
			<div
				class="w-full cursor-pointer rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-gray-100"
				onclick={startEditingClassName}
				role="button"
				tabindex="0"
			>
				{data.className || 'Unnamed Task'}
			</div>
		{/if}
	</div>

	<!-- Fields list with compact styling -->
	<div class="relative max-h-48 overflow-y-auto">
		<!-- Plus button overlay -->
		<div class="absolute right-2 top-0 z-10 flex translate-y-[-50%] items-center bg-white px-1">
			{#if !editingNewField}
				<button
					class="flex h-4 w-4 items-center justify-center rounded-full bg-blue-100 text-xs text-blue-500 hover:bg-blue-200"
					onclick={() => (editingNewField = true)}
					title="Add field"
				>
					<span class="font-bold leading-none">+</span>
				</button>
			{/if}
		</div>

		<div class="p-1.5">
			{#if !currentFields.length && !editingNewField}
				<div class="text-2xs py-1 italic text-gray-400">No fields</div>
			{/if}

			<!-- Existing fields -->
			{#if currentFields.length > 0}
				<div class="space-y-1">
					{#each currentFields as field, index}
						<div class="text-2xs flex items-center justify-between rounded bg-gray-50 px-1 py-0.5">
							<div class="flex items-center gap-1">
								<span class="font-medium">{field.name}</span>
								<span class="text-gray-500">:</span>
								<span class="text-gray-600">{formatFieldType(field.type)}</span>
								{#if !field.required}
									<span class="text-gray-400">?</span>
								{/if}
							</div>
							<button
								class="ml-1 flex h-3 w-3 items-center justify-center rounded-full text-red-400 hover:bg-red-50 hover:text-red-500"
								onclick={() => deleteField(index)}
								title="Remove field"
							>
								<span class="leading-none">×</span>
							</button>
						</div>
					{/each}
				</div>
			{/if}

			<!-- New field form -->
			{#if editingNewField}
				<div class="mt-1 rounded border border-gray-200 bg-gray-50 p-1">
					<div class="mb-1 flex items-center gap-1">
						<input
							type="text"
							bind:value={newFieldName}
							onblur={validateNewFieldName}
							placeholder="name"
							class="text-2xs w-full flex-grow rounded border border-gray-200 px-1 py-0.5 {newFieldNameError
								? 'border-red-500'
								: ''}"
						/>

						<select
							bind:value={newFieldType}
							class="text-2xs w-16 rounded border border-gray-200 px-1 py-0.5"
						>
							{#each Object.entries(BASE_TYPE_LABELS) as [value, label]}
								<option {value}>{label}</option>
							{/each}
						</select>

						<div class="flex items-center">
							<label class="text-2xs ml-1">List</label>
							<input
								type="checkbox"
								bind:checked={newFieldIsList}
								class="ml-0.5 h-2.5 w-2.5 rounded"
							/>
						</div>
					</div>

					{#if newFieldNameError}
						<div class="text-2xs mb-1 text-red-500">{newFieldNameError}</div>
					{/if}

					<div class="flex items-center justify-between">
						<div class="text-2xs flex items-center">
							<input
								type="checkbox"
								id="newFieldRequired{id}"
								bind:checked={newFieldRequired}
								class="h-2.5 w-2.5 rounded"
							/>
							<label for="newFieldRequired{id}" class="text-2xs ml-1">Required</label>
						</div>

						<div class="flex justify-end space-x-1">
							<button
								class="text-2xs rounded bg-gray-200 px-1 py-0.5 hover:bg-gray-300"
								onclick={cancelNewField}
							>
								Cancel
							</button>
							<button
								class="text-2xs rounded bg-blue-500 px-1 py-0.5 text-white hover:bg-blue-600"
								onclick={addField}
							>
								Add
							</button>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	/* Additional utility class for extra small text */
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
