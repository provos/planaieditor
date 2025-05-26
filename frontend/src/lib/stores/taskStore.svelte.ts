import { persistedState } from '$lib/utils/persist.svelte';
import { taskClassNamesStore } from './classNameStore.svelte';
import { taskImports, type TaskImport } from './taskImportStore.svelte';
import { areSetsEqual } from '$lib/utils/utils';
import { untrack } from 'svelte';

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
	type: 'task' | 'taskimport';
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

export function getTaskById(id: string): Task | undefined {
	return tasks.find((task: Task) => task.id === id);
}

// Update the task class names store when the tasks or task imports change
$effect.root(() => {
	$effect(() => {
		// Get all currently defined task class names
		const localTaskClassNames = new Set(tasks.map((task: Task) => task.className));
		const importedTaskClassNames = new Set(
			taskImports.map((taskImport: TaskImport) => taskImport.className)
		);

		untrack(() => {
			// Merge the two sets
			const allTaskClassNames = new Set([...localTaskClassNames, ...importedTaskClassNames]);

			if (!areSetsEqual(allTaskClassNames, taskClassNamesStore)) {
				taskClassNamesStore.clear();
				allTaskClassNames.forEach((name) => taskClassNamesStore.add(name));
			}
		});
	});
});
