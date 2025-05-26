<script lang="ts">
	import { closeSplitPane } from '$lib/stores/splitPaneStore.svelte';
	import EditPane from './EditPane.svelte';
	import ListPane from './ListPane.svelte';
	import { Splitpanes, Pane } from 'svelte-splitpanes';
	import X from 'phosphor-svelte/lib/X';
</script>

<div class="relative h-full">
	<button
		onclick={closeSplitPane}
		class="absolute right-2 top-2 z-10 rounded-sm p-1 text-gray-500 transition-colors duration-150 hover:bg-gray-300/50 hover:text-gray-700"
		title="Close panel"
	>
		<X size={14} />
	</button>

	<Splitpanes horizontal={true}>
		<Pane>
			<EditPane />
		</Pane>
		<Pane minSize={25} maxSize={75}>
			<ListPane />
		</Pane>
	</Splitpanes>
</div>
