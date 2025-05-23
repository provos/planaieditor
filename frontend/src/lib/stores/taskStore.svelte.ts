import { persistedState } from '$lib/utils/persist.svelte';

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
    tasks[tasks.indexOf(task)] = task;
}

export function getTaskByName(name: string): Task | undefined {
    return tasks.find((task: Task) => task.className === name);
}