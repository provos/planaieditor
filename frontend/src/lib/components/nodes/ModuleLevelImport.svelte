<script lang="ts">
    import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
    import { NodeResizer } from '@xyflow/svelte';
    import HeaderIcon from '$lib/components/HeaderIcon.svelte';


    export interface ModuleLevelImportData {
        code: string;
        nodeId: string;
    }

    let { id, data } = $props<{
        id: string,
        data: ModuleLevelImportData
    }>();

    let handleCodeUpdate = (code: string) => {
        data.code = code;
    };

</script>

<div
	class="modulelevelimport-node flex h-full flex-col rounded-md border border-gray-300 bg-white shadow-md"
>
	<!-- Node Resizer -->
	<NodeResizer
		minWidth={200}
		minHeight={150}
		handleClass="resize-handle-modulelevelimport"
		lineClass="resize-line-modulelevelimport"
	/>

    <!-- Header with Task Type Selector -->
	<div class="flex-none border-b bg-emerald-100 p-1">
		<HeaderIcon workerType={'modulelevelimport'} />
		<div class="w-full cursor-pointer rounded px-1 py-0.5 text-center text-xs font-medium hover:bg-gray-100">
            Module Level Import
        </div>
	</div>

    <!-- JSON Data Editor -->
    <div class="relative flex h-full min-h-0 flex-col p-1.5">
        <EditableCodeSection
            title="Module Level Import"
            code={data.code}
            language="python"
            onUpdate={handleCodeUpdate}
        />
    </div>
</div>

<style>
	/* Use global styles defined elsewhere for handles/resizers if consistent */
	:global(.resize-handle-modulelevelimport) {
		width: 12px !important;
		height: 12px !important;
		border-radius: 3px !important;
		border: 2px solid var(--color-emerald-200) !important;
		background-color: rgba(100, 149, 237, 0.2) !important;
	}

	:global(.resize-line-modulelevelimport) {
		border-color: var(--color-emerald-200) !important;
		border-width: 2px !important;
	}
</style>