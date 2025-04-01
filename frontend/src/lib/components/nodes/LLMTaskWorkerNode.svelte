<script lang="ts">
	import BaseWorkerNode from '$lib/components/nodes/BaseWorkerNode.svelte';
	import EditableCodeSection from '$lib/components/EditableCodeSection.svelte';
	import type { BaseWorkerData } from '$lib/components/nodes/BaseWorkerNode.svelte';

	// Extend the base data interface
	interface LLMWorkerData extends BaseWorkerData {
		prompt: string;
		systemPrompt: string;
	}

	let { id, data } = $props<{
		id: string;
		data: LLMWorkerData;
	}>();

	// Ensure additional fields are initialized
	if (!data.prompt) {
		data.prompt = '';
	}
	if (!data.systemPrompt) {
		data.systemPrompt = '';
	}

	// Simplified handlePromptUpdate for the new component
	function handlePromptUpdate(newCode: string) {
		data.prompt = newCode;
	}

	// Simplified handleSystemPromptUpdate for the new component
	function handleSystemPromptUpdate(newCode: string) {
		data.systemPrompt = newCode;
	}
</script>

<BaseWorkerNode {id} {data} defaultName="LLMTaskWorker" minHeight={250}>
	<!-- Prompt and System Prompt Sections using new component -->
	<div class="flex min-h-0 flex-grow flex-col space-y-2 overflow-hidden">
		<EditableCodeSection
			title="Prompt"
			code={data.prompt}
			language="markdown"
			onUpdate={handlePromptUpdate}
		/>
		<EditableCodeSection
			title="System Prompt"
			code={data.systemPrompt}
			language="markdown"
			onUpdate={handleSystemPromptUpdate}
		/>
	</div>
</BaseWorkerNode>
