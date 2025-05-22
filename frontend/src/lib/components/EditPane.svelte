<script lang="ts">
    import { splitPaneConfig } from '$lib/stores/splitPaneStore.svelte';
    import ToolConfig from './ToolConfig.svelte';

    const upperNodeId = $derived(splitPaneConfig.upperNodeId);
    const upperNodeType = $derived(splitPaneConfig.upperNodeType);    
</script>

<div class="h-full overflow-auto">
    {#if upperNodeType === 'tool' && upperNodeId}
        <ToolConfig id={upperNodeId} />
    {:else if upperNodeType === 'task' && upperNodeId}
        Nothing to see here yet
    {:else}
        <div class="prose prose-xs">
            Click on a tool or task in the list at the bottom to edit it.
        </div>
    {/if}
</div>