<script lang="ts">
    import { getNodeIconStyle } from '$lib/utils/defaults';

    let { workerType } = $props<{ workerType: string }>();

    const nodeIconStyle = getNodeIconStyle(workerType || 'default');
</script>

<div class="absolute left-1.5 top-1.5 z-10 flex items-center justify-between">
    <nodeIconStyle.icon size={16} weight="fill" class={nodeIconStyle.color}/>
</div>