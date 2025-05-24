<script lang="ts">
	import {
		taskImports as taskImportsStore,
		addTaskImport,
		removeTaskImport,
		type TaskImport
	} from '$lib/stores/taskImportStore.svelte';
	import { splitPaneConfig } from '$lib/stores/splitPaneStore.svelte';
	import BaseList from './BaseList.svelte';
	import { generateUniqueName } from '$lib/utils/utils';
	import { taskClassNamesStore } from '$lib/stores/classNameStore.svelte';

	function createNewTaskImport() {
		const newTask: TaskImport = {
			id: `taskimport-${crypto.randomUUID()}`,
			type: 'taskimport',
			className: '',
			modulePath: '',
			availableClasses: [],
			fields: []
		};
		addTaskImport(newTask);
		splitPaneConfig.upperNodeId = newTask.id;
		splitPaneConfig.upperNodeType = 'taskimport';
	}

	function deleteTaskImport(task: TaskImport) {
		removeTaskImport(task);
		if (splitPaneConfig.upperNodeId === task.id) {
			splitPaneConfig.upperNodeId = null;
			splitPaneConfig.upperNodeType = null;
		}
	}

	function selectTaskImport(task: TaskImport) {
		splitPaneConfig.upperNodeId = task.id;
		splitPaneConfig.upperNodeType = 'taskimport';
	}

	function isTaskImportSelected(task: TaskImport): boolean {
		return (
			splitPaneConfig.upperNodeId === task.id && splitPaneConfig.upperNodeType === 'taskimport'
		);
	}
</script>

<BaseList
	items={taskImportsStore}
	onSelect={selectTaskImport}
	onDelete={deleteTaskImport}
	onCreate={createNewTaskImport}
	emptyMessage="No tasks defined yet. Click the plus button below to add one."
	createButtonTitle="Add new task"
	getName={(task) => task.className}
	getId={(task) => task.id}
	isSelected={isTaskImportSelected}
/>
