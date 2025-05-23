<script lang="ts">
	import {
		tasks as tasksStore,
		addTask,
		removeTask,
		type Task
	} from '$lib/stores/taskStore.svelte';
	import { splitPaneConfig } from '$lib/stores/splitPaneStore.svelte';
	import BaseList from './BaseList.svelte';

	function createNewTask() {
		const newTask: Task = {
			id: `task-${Date.now()}`,
			className: 'NewTask',
			fields: []
		};
		addTask(newTask);
		splitPaneConfig.upperNodeId = newTask.id;
		splitPaneConfig.upperNodeType = 'task';
	}

	function deleteTask(task: Task) {
		removeTask(task);
		if (splitPaneConfig.upperNodeId === task.id) {
			splitPaneConfig.upperNodeId = null;
			splitPaneConfig.upperNodeType = null;
		}
	}

	function selectTask(task: Task) {
		splitPaneConfig.upperNodeId = task.id;
		splitPaneConfig.upperNodeType = 'task';
	}

	function isTaskSelected(task: Task): boolean {
		return splitPaneConfig.upperNodeId === task.id && splitPaneConfig.upperNodeType === 'task';
	}
</script>

<BaseList
	items={tasksStore}
	onSelect={selectTask}
	onDelete={deleteTask}
	onCreate={createNewTask}
	emptyMessage="No tasks defined yet. Click the plus button below to add one."
	createButtonTitle="Add new task"
	getName={(task) => task.className}
	getId={(task) => task.id}
	isSelected={isTaskSelected}
/>
