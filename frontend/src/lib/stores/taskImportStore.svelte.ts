import { persistedState } from '$lib/utils/persist.svelte';
import type { Task as TaskType } from './taskStore.svelte';
import { taskClassNamesStore } from './classNameStore.svelte';
import { tasks } from './taskStore.svelte';

export interface TaskImport extends TaskType {
	modulePath?: string;
	isImplicit?: boolean;  // this is not user defined but was auto-magically added by the backend
	availableClasses?: string[];
}

export const taskImports = persistedState<TaskImport[]>('taskImports', [], { storage: 'local' });

export function addTaskImport(task: TaskImport) {
	taskImports.push(task);
}

export function removeTaskImport(task: TaskImport) {
	taskImports.splice(taskImports.indexOf(task), 1);
}

export function updateTaskImport(task: TaskImport) {
	const index = taskImports.findIndex((t) => t.id === task.id);
	if (index !== -1) {
		taskImports[index] = task;
	}
}

export function getTaskImportByName(name: string): TaskImport | undefined {
	return taskImports.find((item: TaskImport) => item.className === name);
}

export function getTaskImportById(id: string): TaskImport | undefined {
	return taskImports.find((item: TaskImport) => item.id === id);
}

// Update the task class names store when the task imports change
$effect.root(() => {
	$effect(() => {
		// Get all currently imported task class names
		const importedTaskClassNames = new Set(
			taskImports.map((taskImport: TaskImport) => taskImport.className)
		);

		// Remove all imported task names that are no longer present
		const currentTaskClassNames = Array.from(taskClassNamesStore);
		currentTaskClassNames.forEach((name) => {
			// Check if this name exists in local tasks to avoid removing local names
			const isLocal = tasks && Array.from(tasks).some((task: any) => task.className === name);
			if (!isLocal && !importedTaskClassNames.has(name)) {
				taskClassNamesStore.delete(name);
			}
		});

		// Add all current imported task names
		importedTaskClassNames.forEach((name) => taskClassNamesStore.add(name));
	});
});
