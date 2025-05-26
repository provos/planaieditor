<script lang="ts">
	import { isValidPythonClassName, isValidPythonIdentifier } from '$lib/utils/validation';
	import { taskClassNamesStore } from '$lib/stores/classNameStore.svelte';
	import {
		tasks as tasksStore,
		updateTask,
		type Task,
		type Field
	} from '$lib/stores/taskStore.svelte';
	import { taskImports as taskImportsStore } from '$lib/stores/taskImportStore.svelte';
	import Plus from 'phosphor-svelte/lib/Plus';
	import Trash from 'phosphor-svelte/lib/Trash';
	import PencilSimple from 'phosphor-svelte/lib/PencilSimple';
	import type { Snippet } from 'svelte';

	// Define basic field types
	type BaseFieldType = 'string' | 'integer' | 'float' | 'boolean' | 'literal';
	// Enhanced field type can be a basic type or a custom Task name
	type FieldType = string;

	let {
		id,
		allowEditing = true,
		embedded = false,
		children,
		styleClasses
	} = $props<{
		id: string;
		allowEditing?: boolean;
		embedded?: boolean;
		children?: Snippet;
		styleClasses?: string;
	}>();

	const task: Task | undefined = $derived(
		tasksStore.find((t) => t.id === id) || taskImportsStore.find((t) => t.id === id)
	);

	// State variables
	let editingClassName = $state(false);
	let classNameError = $state('');
	let editingFieldIndex = $state<number | null>(null);
	let editingFieldName = $state('');
	let editingFieldType = $state<FieldType>('string');
	let editingFieldIsList = $state(false);
	let editingFieldRequired = $state(true);
	let editingFieldDescription = $state<string | undefined>(undefined);
	let fieldNameError = $state('');
	let tempClassName = $state('');

	// Update tempClassName when task changes
	$effect(() => {
		if (task) {
			tempClassName = task.className;
		}
	});

	// Track current fields for rendering
	let currentFields = $derived<Field[]>(task?.fields || []);

	// Field type options
	const BASE_TYPE_LABELS: Record<BaseFieldType, string> = {
		string: 'str',
		integer: 'int',
		float: 'float',
		boolean: 'bool',
		literal: 'Literal'
	};

	// Available custom task types
	let availableTaskTypes = $state<string[]>([]);

	// For editing literal values
	let literalValueInput = $state('');
	let editingLiteralValues = $state<string[]>([]);

	// Watch for task types
	$effect(() => {
		availableTaskTypes = Array.from(taskClassNamesStore);
	});

	// Computed field type options for dropdowns
	let fieldTypeOptions = $state<Array<{ value: string; label: string }>>([]);

	// Update options whenever availableTaskTypes changes
	$effect(() => {
		// Base primitive types
		const primitiveOptions = Object.entries(BASE_TYPE_LABELS).map(([value, label]) => ({
			value,
			label
		}));

		// Custom Task class types
		const customOptions = availableTaskTypes
			.filter((name) => name !== task?.className) // Prevent self-references
			.map((name) => ({
				value: name,
				label: name
			}));

		// Combine and sort (primitives first, then custom types alphabetically)
		fieldTypeOptions = [
			...primitiveOptions,
			...customOptions.sort((a, b) => a.label.localeCompare(b.label))
		];
	});

	function startEditingClassName() {
		if (!task || !allowEditing) return;
		tempClassName = task.className;
		editingClassName = true;
	}

	function validateClassName(name: string): boolean {
		// First check if it's a valid Python class name
		if (!isValidPythonClassName(name)) {
			classNameError = 'Invalid Python class name';
			return false;
		}

		// Then check if it's unique among all tasks
		const isDuplicate = tasksStore.some((t) => t.id !== task?.id && t.className === name);

		if (isDuplicate) {
			classNameError = 'Class name already exists';
			return false;
		}

		classNameError = '';
		return true;
	}

	function updateClassName() {
		if (!task || task.className === tempClassName) {
			editingClassName = false;
			classNameError = '';
			return;
		}

		if (!validateClassName(tempClassName)) {
			return;
		}

		const updatedTask = { ...task, className: tempClassName };
		updateTask(updatedTask);
		editingClassName = false;
	}

	function cancelEditingClassName() {
		if (task) {
			tempClassName = task.className;
		}
		classNameError = '';
		editingClassName = false;
	}

	function startEditingField(index: number) {
		if (!task || !allowEditing) return;
		const field = task.fields[index];
		editingFieldIndex = index;
		editingFieldName = field.name;
		editingFieldIsList = field.isList;
		editingFieldType = field.type;
		editingFieldDescription = field.description;
		editingFieldRequired = field.required;
		editingLiteralValues = field.literalValues ? [...field.literalValues] : [];
		fieldNameError = '';
	}

	function startAddingField() {
		if (!task || !allowEditing) return;
		editingFieldIndex = -1;
		editingFieldName = '';
		editingFieldType = 'string';
		editingFieldIsList = false;
		editingFieldRequired = true;
		fieldNameError = '';
		editingFieldDescription = undefined;
		editingLiteralValues = [];
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
		if (task?.fields.some((f: Field, i: number) => f.name === name && i !== currentIndex)) {
			fieldNameError = 'Field name exists';
			return false;
		}

		fieldNameError = '';
		return true;
	}

	function saveField() {
		if (!task || !validateFieldName(editingFieldName, editingFieldIndex!)) return;

		const newField: Field = {
			name: editingFieldName,
			type: editingFieldType,
			isList: editingFieldIsList,
			required: editingFieldRequired,
			description: editingFieldDescription || undefined
		};

		// Add literal values if it's a literal type
		if (editingFieldType === 'literal' && editingLiteralValues.length > 0) {
			newField.literalValues = [...editingLiteralValues];
		}

		let updatedFields: Field[];
		if (editingFieldIndex === -1) {
			// Add new field
			updatedFields = [...task.fields, newField];
		} else {
			// Update existing field
			updatedFields = task.fields.map((field: Field, i: number) =>
				i === editingFieldIndex ? newField : field
			);
		}

		const updatedTask = { ...task, fields: updatedFields };
		updateTask(updatedTask);

		// Reset form
		cancelFieldEditing();
	}

	function cancelFieldEditing() {
		editingFieldIndex = null;
		editingFieldName = '';
		fieldNameError = '';
		editingFieldDescription = undefined;
		editingLiteralValues = [];
		literalValueInput = '';
	}

	function deleteField(index: number) {
		if (!task) return;
		const updatedFields = task.fields.filter((_: Field, i: number) => i !== index);
		const updatedTask = { ...task, fields: updatedFields };
		updateTask(updatedTask);
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
		let baseLabel = field.type;

		// Check if it's a primitive type
		if (Object.prototype.hasOwnProperty.call(BASE_TYPE_LABELS, field.type)) {
			baseLabel = BASE_TYPE_LABELS[field.type as BaseFieldType];
		}
		// Otherwise, use the custom type name directly

		if (field.type === 'literal' && field.literalValues?.length) {
			// For Literal types, show some of the values
			const displayValues = field.literalValues.slice(0, 3);
			const moreIndicator = field.literalValues.length > 3 ? ', ...' : '';
			return `Literal[${displayValues.map((v) => `"${v}"`).join(', ')}${moreIndicator}]`;
		} else if (field.isList) {
			return `List[${baseLabel}]`;
		}
		return baseLabel;
	}

	// Add a new literal value to the current field being edited
	function addLiteralValue() {
		if (!literalValueInput.trim()) return;

		// Add the value if it's not already in the list
		if (!editingLiteralValues.includes(literalValueInput.trim())) {
			editingLiteralValues = [...editingLiteralValues, literalValueInput.trim()];
		}
		literalValueInput = ''; // Clear the input
	}

	// Remove a literal value
	function removeLiteralValue(index: number) {
		editingLiteralValues = editingLiteralValues.filter((_, i) => i !== index);
	}

	// Handle keydown for literal value input
	function handleLiteralKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault(); // Prevent form submission
			addLiteralValue();
		}
	}
</script>

{#if task}
	<div class="flex h-full flex-col bg-white {styleClasses}">
		{#if !embedded}
			<!-- Header with editable class name -->
			<div class="flex-none border-b border-gray-200 bg-gray-50 p-1.5">
				{#if editingClassName}
					<div class="flex flex-col">
						<input
							type="text"
							bind:value={tempClassName}
							onblur={updateClassName}
							onkeydown={handleClassNameKeydown}
							class="w-full rounded border border-gray-200 bg-white px-1.5 py-1 text-sm font-medium {classNameError
								? 'border-red-500'
								: ''}"
						/>
						{#if classNameError}
							<div class="mt-0.5 text-xs text-red-500">{classNameError}</div>
						{/if}
					</div>
				{:else if allowEditing}
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<div
						class="w-full cursor-pointer rounded px-1.5 py-1 text-center text-sm font-medium hover:bg-gray-100"
						onclick={startEditingClassName}
						data-testid="task-name-value"
						role="button"
						tabindex={0}
					>
						{task.className || 'Unnamed Task'}
					</div>
				{:else}
					<!-- Read-only class name when editing is disabled -->
					<div class="w-full rounded px-1.5 py-1 text-center text-sm font-medium text-gray-700">
						{task.className || 'Unnamed Task'}
					</div>
				{/if}
			</div>
		{:else if children}
			{@render children()}
		{/if}

		<!-- Fields list -->
		<div class="relative h-full min-h-0 flex-grow overflow-y-auto p-1.5">
			{#if !currentFields.length && editingFieldIndex !== -1}
				<div class="text-2xs py-0.5 text-gray-400 italic">No fields</div>
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
								/>

								<select
									bind:value={editingFieldType}
									class="text-2xs w-auto max-w-xs min-w-[4rem] rounded border border-gray-200 px-1 py-0.5"
								>
									{#each fieldTypeOptions as option}
										<option value={option.value}>{option.label}</option>
									{/each}
								</select>

								<div class="flex items-center">
									<label for="fieldIsList{id}{index}" class="text-2xs ml-0.5">List</label>
									<input
										id="fieldIsList{id}{index}"
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

							<!-- Literal Values Editor (only shown when type is 'literal') -->
							{#if editingFieldType === 'literal'}
								<div class="mb-2 border-t border-gray-100 pt-1">
									<div class="text-2xs mb-0.5 font-medium">Literal Values:</div>
									<div class="mb-1 flex gap-1">
										<input
											type="text"
											bind:value={literalValueInput}
											placeholder="Add value..."
											class="text-2xs flex-1 rounded border border-gray-200 px-1 py-0.5"
											onkeydown={handleLiteralKeydown}
										/>
										<button
											class="text-2xs rounded bg-blue-100 px-1 py-0.5 text-blue-700 hover:bg-blue-200"
											onclick={addLiteralValue}
										>
											Add
										</button>
									</div>

									{#if editingLiteralValues.length === 0}
										<div class="text-2xs text-gray-400 italic">No values added yet</div>
									{:else}
										<div class="flex flex-wrap gap-1">
											{#each editingLiteralValues as value, idx}
												<div
													class="text-2xs inline-flex items-center rounded bg-gray-100 px-1 py-0.5"
												>
													<span class="mr-1">{value}</span>
													<button
														class="text-gray-500 hover:text-red-500"
														onclick={() => removeLiteralValue(idx)}
														title="Remove value"
													>
														×
													</button>
												</div>
											{/each}
										</div>
									{/if}
								</div>
							{/if}

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
						<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
						<div
							class="text-2xs group flex {allowEditing
								? 'cursor-pointer'
								: ''} items-center justify-between rounded bg-gray-50 px-1 py-0.5 {allowEditing
								? 'hover:bg-gray-100'
								: ''}"
							onclick={allowEditing ? () => startEditingField(index) : undefined}
							role={allowEditing ? 'button' : undefined}
							tabindex={allowEditing ? 0 : -1}
						>
							<div class="flex items-center gap-1">
								<span class="font-medium">{field.name}</span>
								<span class="text-gray-500">:</span>
								<span class="text-gray-600">{formatFieldType(field)}</span>
								{#if field.description}
									<span
										class="ml-1 truncate text-ellipsis text-gray-400 italic"
										title={field.description}
									>
										({field.description})
									</span>
								{/if}
								{#if !field.required}
									<span class="text-gray-400">?</span>
								{/if}
							</div>
							{#if allowEditing}
								<div class="flex items-center">
									<button
										class="ml-1 flex h-3.5 w-3.5 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-gray-200 hover:text-blue-500"
										onclick={(e) => {
											e.stopPropagation();
											startEditingField(index);
										}}
										title="Edit field"
									>
										<PencilSimple size={8} weight="bold" />
									</button>
									<button
										class="ml-1 flex h-3.5 w-3.5 items-center justify-center rounded-full text-gray-400 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-50 hover:text-red-500"
										onclick={(e) => {
											e.stopPropagation();
											deleteField(index);
										}}
										title="Remove field"
									>
										<Trash size={8} weight="bold" />
									</button>
								</div>
							{/if}
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
							/>

							<select
								bind:value={editingFieldType}
								class="text-2xs w-auto max-w-xs min-w-[4rem] rounded border border-gray-200 px-1 py-0.5"
							>
								{#each fieldTypeOptions as option}
									<option value={option.value}>{option.label}</option>
								{/each}
							</select>

							<div class="flex items-center">
								<label for="newFieldIsList{id}" class="text-2xs ml-0.5">List</label>
								<input
									id="newFieldIsList{id}"
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

						<!-- Literal Values Editor (only shown when type is 'literal') -->
						{#if editingFieldType === 'literal'}
							<div class="mb-2 border-t border-gray-100 pt-1">
								<div class="text-2xs mb-0.5 font-medium">Literal Values:</div>
								<div class="mb-1 flex gap-1">
									<input
										type="text"
										bind:value={literalValueInput}
										placeholder="Add value..."
										class="text-2xs flex-1 rounded border border-gray-200 px-1 py-0.5"
										onkeydown={handleLiteralKeydown}
									/>
									<button
										class="text-2xs rounded bg-blue-100 px-1 py-0.5 text-blue-700 hover:bg-blue-200"
										onclick={addLiteralValue}
									>
										Add
									</button>
								</div>

								{#if editingLiteralValues.length === 0}
									<div class="text-2xs text-gray-400 italic">No values added yet</div>
								{:else}
									<div class="flex flex-wrap gap-1">
										{#each editingLiteralValues as value, idx}
											<div
												class="text-2xs inline-flex items-center rounded bg-gray-100 px-1 py-0.5"
											>
												<span class="mr-1">{value}</span>
												<button
													class="text-gray-500 hover:text-red-500"
													onclick={() => removeLiteralValue(idx)}
													title="Remove value"
												>
													×
												</button>
											</div>
										{/each}
									</div>
								{/if}
							</div>
						{/if}

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
			{#if editingFieldIndex === null && allowEditing}
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

		<!-- Error Display Area -->
		{#if task.error}
			<div class="mt-auto flex-none border-t border-red-200 bg-red-50 p-1.5">
				<p class="text-2xs font-semibold text-red-700">Error:</p>
				<p class="text-2xs text-red-600">{task.error}</p>
			</div>
		{/if}
	</div>
{:else}
	<div class="flex h-full items-center justify-center p-4">
		<p class="text-gray-500">Select a task to configure it.</p>
	</div>
{/if}

<style>
	/* Additional utility class for extra small text */
	.text-2xs {
		font-size: 0.65rem;
		line-height: 1rem;
	}
</style>
