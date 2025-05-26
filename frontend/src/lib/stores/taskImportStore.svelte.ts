import { persistedState } from '$lib/utils/persist.svelte';
import type { Task as TaskType } from './taskStore.svelte';

export interface TaskImport extends TaskType {
	modulePath?: string;
	isImplicit?: boolean; // this is not user defined but was auto-magically added by the backend
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

// Update the task class names store when the task imports change - this happens in taskStore.svelte.ts
