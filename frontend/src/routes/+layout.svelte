<script lang="ts">
	import { onMount } from 'svelte';
	import { initializeMonaco } from '$lib/stores/monacoStore.svelte';
	import '../app.css';
	import { SvelteFlowProvider } from '@xyflow/svelte';

	onMount(() => {
		console.log('Root layout mounted, initializing Monaco...');
		initializeMonaco();
	});
</script>

<SvelteFlowProvider>
	<slot />
</SvelteFlowProvider>
