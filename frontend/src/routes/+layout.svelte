<script lang="ts">
	import '../app.css';
	import { SvelteFlowProvider } from '@xyflow/svelte';
	export let data;
</script>

<SvelteFlowProvider>
	<slot />
</SvelteFlowProvider>
