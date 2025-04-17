<script lang="ts">
	import '../app.css';
	import { SvelteFlowProvider } from '@xyflow/svelte';
</script>

<SvelteFlowProvider>
	<slot />
</SvelteFlowProvider>
