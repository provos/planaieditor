import { persistedState } from '$lib/utils/persist.svelte';
import { taskClassNamesStore } from './classNameStore.svelte';
import { taskImports } from './taskImportStore.svelte';

// Define basic field types
export type BaseFieldType = 'string' | 'integer' | 'float' | 'boolean' | 'literal';
// Enhanced field type can be a basic type or a custom Task name
export type FieldType = string;

export interface Field {
	name: string;
	type: FieldType;
	isList: boolean;
	required: boolean;
	description?: string;
	literalValues?: string[]; // Add support for Literal types with predefined values
}

export interface Task {
	id: string;
	className: string;
	fields: Field[];
	error?: string;
}

export const tasks = persistedState<Task[]>('tasks', [], { storage: 'local' });

export function addTask(task: Task) {
	tasks.push(task);
}

export function removeTask(task: Task) {
	tasks.splice(tasks.indexOf(task), 1);
}

export function updateTask(task: Task) {
	const index = tasks.findIndex((t) => t.id === task.id);
	if (index !== -1) {
		tasks[index] = task;
	}
}

export function getTaskByName(name: string): Task | undefined {
	return tasks.find((task: Task) => task.className === name);
}

// Update the task class names store when the tasks change
$effect.root(() => {
	$effect(() => {
		// Get all currently defined task class names
		const localTaskClassNames = new Set(tasks.map((task: Task) => task.className));

		// Remove all local task names that are no longer present
		const currentTaskClassNames = Array.from(taskClassNamesStore);
		currentTaskClassNames.forEach((name) => {
			// Check if this name exists in taskImports to avoid removing imported names
			const isImported =
				taskImports &&
				Array.from(taskImports).some((taskImport: any) => taskImport.className === name);
			if (!isImported && !localTaskClassNames.has(name)) {
				taskClassNamesStore.delete(name);
			}
		});

		// Add all current local task names
		localTaskClassNames.forEach((name) => taskClassNamesStore.add(name));
	});
});
