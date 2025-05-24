import { persistedState } from '$lib/utils/persist.svelte';
import type { Task as TaskType} from './taskStore.svelte';

export interface TaskImport extends TaskType {
    modulePath?: string;
    isImplicit?: boolean;
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
    taskImports[taskImports.indexOf(task)] = task;
}

export function getTaskImportByName(name: string): TaskImport | undefined {
    return taskImports.find((item: TaskImport) => item.className === name);
}