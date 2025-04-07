<script lang="ts">
	import { Handle, Position, NodeResizer } from '@xyflow/svelte';
	import { isValidPythonClassName, isValidPythonIdentifier } from '$lib/utils/validation';
	import { allClassNames } from '$lib/stores/classNameStore';
	import { getColorForType } from '$lib/utils/colorUtils';
	import Plus from 'phosphor-svelte/lib/Plus';
	import Trash from 'phosphor-svelte/lib/Trash';
	import PencilSimple from 'phosphor-svelte/lib/PencilSimple';

	type BaseFieldType = 'string' | 'integer' | 'float';
	type FieldType = BaseFieldType;

	interface Field {
		name: string;
		type: FieldType;
		isList: boolean;
		required: boolean;
		description?: string;
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
	let editingFieldIndex = $state<number | null>(null);
	let editingFieldName = $state('');
	let editingFieldType = $state<BaseFieldType>('string');
	let editingFieldIsList = $state(false);
	let editingFieldRequired = $state(true);
	let editingFieldDescription = $state<string | undefined>(undefined);
	let fieldNameError = $state('');
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

	function startEditingField(index: number) {
		const field = data.fields[index];
		editingFieldIndex = index;
		editingFieldName = field.name;
		editingFieldIsList = field.isList;
		editingFieldType = field.type as BaseFieldType;
		editingFieldDescription = field.description;
		editingFieldRequired = field.required;
		fieldNameError = '';
	}

	function startAddingField() {
		editingFieldIndex = -1;
		editingFieldName = '';
		editingFieldType = 'string';
		editingFieldIsList = false;
		editingFieldRequired = true;
		fieldNameError = '';
		editingFieldDescription = undefined;
	}

	function validateFieldName(name: string, currentIndex: number): boolean {
		if (!name) {
			fieldNameError = 'Required';
			return false;
		}

		if (!isValidPythonIdentifier(name)) {
			fieldNameError = 'Invalid Python identifier';
			return false;
		}

		// Check if the name exists in other fields (ignore current field being edited)
		if (data.fields.some((f: Field, i: number) => f.name === name && i !== currentIndex)) {
			fieldNameError = 'Field name exists';
			return false;
		}

		fieldNameError = '';
		return true;
	}

	function saveField() {
		if (!validateFieldName(editingFieldName, editingFieldIndex!)) return;

		const newField = {
			name: editingFieldName,
			type: editingFieldType,
			isList: editingFieldIsList,
			required: editingFieldRequired,
			description: editingFieldDescription || undefined
		};

		if (editingFieldIndex === -1) {
			// Add new field
			data.fields = [...data.fields, newField];
		} else {
			// Update existing field
			data.fields = data.fields.map((field: Field, i: number) =>
				i === editingFieldIndex ? newField : field
			);
		}

		// Update our local tracking state
		currentFields = [...data.fields];

		// Reset form
		cancelFieldEditing();
	}

	function cancelFieldEditing() {
		editingFieldIndex = null;
		editingFieldName = '';
		fieldNameError = '';
		editingFieldDescription = undefined;
	}

	function deleteField(index: number) {
		data.fields = data.fields.filter((_: Field, i: number) => i !== index);
		currentFields = [...data.fields];
	}

	// Handle keydown for class name editing
	function handleClassNameKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			updateClassName();
		} else if (event.key === 'Escape') {
			cancelEditingClassName();
		}
	}

	// Handle keydown for field editing
	function handleFieldKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			saveField();
		} else if (event.key === 'Escape') {
			cancelFieldEditing();
		}
	}

	// Format field type for display
	function formatFieldType(field: Field): string {
		if (field.isList) {
			return `List[${BASE_TYPE_LABELS[field.type as BaseFieldType]}]`;
		}
		return BASE_TYPE_LABELS[field.type as BaseFieldType];
	}

	// Update local fields when data.fields changes
	$effect(() => {
		currentFields = [...data.fields];
	});
</script>

<div class="task-node flex h-full flex-col rounded-md border border-gray-300 bg-white shadow-md">
	<!-- Node Resizer -->
	<NodeResizer minWidth={200} minHeight={150} />

	<!-- Node handles -->
	<Handle type="source" position={Position.Right} id="output" style={`background-color: ${getColorForType(data.className)};`}/>

	<!-- Header with editable class name -->
	<div class="flex-none border-b border-gray-200 bg-gray-50 p-1">
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
			<!-- svelte-ignore a11y_click_events_have_key_events -->
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
	<div class="relative h-full min-h-0 flex-grow overflow-y-auto p-1.5">
		{#if !currentFields.length && editingFieldIndex !== -1}
			<div class="text-2xs py-0.5 italic text-gray-400">No fields</div>
		{/if}

		<!-- Existing fields -->
		<div class="space-y-1">
			{#each currentFields as field, index}
				{#if editingFieldIndex === index}
					<div class="rounded border border-blue-200 bg-blue-50 p-1">
						<div class="mb-1 flex items-center gap-1">
							<input
								type="text"
								bind:value={editingFieldName}
								onkeydown={handleFieldKeydown}
								class="text-2xs w-full flex-grow rounded border border-gray-200 px-1 py-0.5 {fieldNameError
									? 'border-red-500'
									: ''}"
								autofocus
							/>

							<select
								bind:value={editingFieldType}
								class="text-2xs w-14 rounded border border-gray-200 px-1 py-0.5"
							>
								{#each Object.entries(BASE_TYPE_LABELS) as [value, label]}
									<option {value}>{label}</option>
								{/each}
							</select>

							<div class="flex items-center">
								<label class="text-2xs ml-0.5">List</label>
								<input
									type="checkbox"
									bind:checked={editingFieldIsList}
									class="ml-0.5 h-2.5 w-2.5 rounded"
								/>
							</div>
						</div>

						{#if fieldNameError}
							<div class="text-2xs mb-1 text-red-500">{fieldNameError}</div>
						{/if}

						<!-- Description Input -->
						<div class="mb-1">
							<input
								type="text"
								bind:value={editingFieldDescription}
								placeholder="Description (optional)"
								class="text-2xs w-full rounded border border-gray-200 px-1 py-0.5"
								onkeydown={handleFieldKeydown}
							/>
						</div>

						<div class="flex items-center justify-between">
							<div class="text-2xs flex items-center">
								<input
									type="checkbox"
									id="fieldRequired{id}{index}"
									bind:checked={editingFieldRequired}
									class="h-2.5 w-2.5 rounded"
								/>
								<label for="fieldRequired{id}{index}" class="text-2xs ml-0.5">Required</label>
							</div>

							<div class="flex justify-end space-x-1">
								<button
									class="text-2xs rounded bg-gray-200 px-1 py-0.5 hover:bg-gray-300"
									onclick={cancelFieldEditing}
								>
									Cancel
								</button>
								<button
									class="text-2xs rounded bg-blue-500 px-1 py-0.5 text-white hover:bg-blue-600"
									onclick={saveField}
								>
									Save
								</button>
							</div>
						</div>
					</div>
				{:else}
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<div
						class="text-2xs group flex cursor-pointer items-center justify-between rounded bg-gray-50 px-1 py-0.5 hover:bg-gray-100"
						onclick={() => startEditingField(index)}
						role="button"
						tabindex="0"
					>
						<div class="flex items-center gap-1">
							<span class="font-medium">{field.name}</span>
							<span class="text-gray-500">:</span>
							<span class="text-gray-600">{formatFieldType(field)}</span>
							{#if field.description}
								<span
									class="ml-1 truncate text-ellipsis italic text-gray-400"
									title={field.description}
								>
									({field.description})
								</span>
							{/if}
							{#if !field.required}
								<span class="text-gray-400">?</span>
							{/if}
						</div>
						<div class="flex items-center">
							<button
								class="ml-1 flex h-3.5 w-3.5 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity hover:bg-gray-200 hover:text-blue-500 group-hover:opacity-100"
								onclick={(e) => {
									e.stopPropagation();
									startEditingField(index);
								}}
								title="Edit field"
							>
								<PencilSimple size={8} weight="bold" />
							</button>
							<button
								class="ml-1 flex h-3.5 w-3.5 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
								onclick={(e) => {
									e.stopPropagation();
									deleteField(index);
								}}
								title="Remove field"
							>
								<Trash size={8} weight="bold" />
							</button>
						</div>
					</div>
				{/if}
			{/each}

			<!-- New field form -->
			{#if editingFieldIndex === -1}
				<div class="rounded border border-blue-200 bg-blue-50 p-1">
					<div class="mb-1 flex items-center gap-1">
						<input
							type="text"
							bind:value={editingFieldName}
							onkeydown={handleFieldKeydown}
							placeholder="field_name"
							class="text-2xs w-full flex-grow rounded border border-gray-200 px-1 py-0.5 {fieldNameError
								? 'border-red-500'
								: ''}"
							autofocus
						/>

						<select
							bind:value={editingFieldType}
							class="text-2xs w-14 rounded border border-gray-200 px-1 py-0.5"
						>
							{#each Object.entries(BASE_TYPE_LABELS) as [value, label]}
								<option {value}>{label}</option>
							{/each}
						</select>

						<div class="flex items-center">
							<label class="text-2xs ml-0.5">List</label>
							<input
								type="checkbox"
								bind:checked={editingFieldIsList}
								class="ml-0.5 h-2.5 w-2.5 rounded"
							/>
						</div>
					</div>

					{#if fieldNameError}
						<div class="text-2xs mb-1 text-red-500">{fieldNameError}</div>
					{/if}

					<!-- Description Input for New Field -->
					<div class="mb-1">
						<input
							type="text"
							bind:value={editingFieldDescription}
							placeholder="Description (optional)"
							class="text-2xs w-full rounded border border-gray-200 px-1 py-0.5"
							onkeydown={handleFieldKeydown}
						/>
					</div>

					<div class="flex items-center justify-between">
						<div class="text-2xs flex items-center">
							<input
								type="checkbox"
								id="newFieldRequired{id}"
								bind:checked={editingFieldRequired}
								class="h-2.5 w-2.5 rounded"
							/>
							<label for="newFieldRequired{id}" class="text-2xs ml-0.5">Required</label>
						</div>

						<div class="flex justify-end space-x-1">
							<button
								class="text-2xs rounded bg-gray-200 px-1 py-0.5 hover:bg-gray-300"
								onclick={cancelFieldEditing}
							>
								Cancel
							</button>
							<button
								class="text-2xs rounded bg-blue-500 px-1 py-0.5 text-white hover:bg-blue-600"
								onclick={saveField}
							>
								Add
							</button>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Plus button at the bottom center -->
		{#if editingFieldIndex === null}
			<div class="mt-2 flex justify-center">
				<button
					class="z-10 flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 text-blue-500 shadow-sm hover:bg-blue-200"
					onclick={startAddingField}
					title="Add field"
				>
					<Plus size={12} weight="bold" />
				</button>
			</div>
		{/if}
	</div>
</div>

<style>
	/* Additional utility class for extra small text */
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
