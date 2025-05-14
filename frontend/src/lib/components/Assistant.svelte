<script lang="ts">
	import { X } from 'phosphor-svelte';
	import { closeAssistant } from '$lib/stores/assistantStateStore.svelte';
	import { useStore } from '@xyflow/svelte';
	import type { Node } from '@xyflow/svelte';
	import type { NodeData } from '$lib/components/nodes/TaskNode.svelte';
	import type { DataInputNodeData } from '$lib/components/nodes/DataInputNode.svelte';
	import { onMount } from 'svelte';
	import { findDataInputNodesWithSingleStringField } from '$lib/utils/nodeUtils';
	type MessageType = 'user' | 'assistant';

	interface Message {
		type: MessageType;
		content: string;
		timestamp: Date;
	}

	let messages: Message[] = $state([]);
	let inputMessage: string = $state('');
	let chatContainer: HTMLElement;

	let { nodes } = useStore();
	let dataInputNodes = $state<Node[]>([]);

	onMount(() => {
		nodes.subscribe((nodes) => {
			dataInputNodes = findDataInputNodesWithSingleStringField(nodes);
			console.log(dataInputNodes);
		});
	});

	function sendMessage() {
		if (!inputMessage.trim()) return;

		// Add user message
		messages = [
			...messages,
			{
				type: 'user',
				content: inputMessage,
				timestamp: new Date()
			}
		];

		const userQuery = inputMessage;
		inputMessage = '';

		// Simulate assistant response (dummy function for now)
		setTimeout(() => {
			messages = [
				...messages,
				{
					type: 'assistant',
					content: `This is a dummy response to: "${userQuery}"`,
					timestamp: new Date()
				}
			];
			scrollToBottom();
		}, 1000);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			sendMessage();
		}
	}

	function scrollToBottom() {
		setTimeout(() => {
			if (chatContainer) {
				chatContainer.scrollTop = chatContainer.scrollHeight;
			}
		}, 0);
	}

	$effect(() => {
		if (messages.length) {
			scrollToBottom();
		}
	});
</script>

<div
	class="animate-in fade-in-0 slide-in-from-bottom-5 fixed inset-0 z-50 flex flex-col bg-gray-900/95 p-4 backdrop-blur-sm duration-200"
>
	<div class="mb-4 flex items-center justify-between">
		<h2 class="text-xl font-semibold text-white">Assistant Mode</h2>
		<button
			class="rounded-full p-2 text-gray-300 transition-colors hover:bg-gray-700 hover:text-white"
			onclick={closeAssistant}
		>
			<X size={24} weight="bold" />
		</button>
	</div>

	<div
		class="scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-transparent mb-4 flex-1 overflow-y-auto pr-2"
		bind:this={chatContainer}
	>
		<div class="flex flex-col space-y-4">
			{#each messages as message, i (i)}
				<div
					class={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in-50 slide-in-from-${message.type === 'user' ? 'right' : 'left'}-5 duration-200`}
				>
					<div
						class={`max-w-[80%] rounded-lg p-3 ${
							message.type === 'user'
								? 'rounded-tr-none bg-blue-600 text-white'
								: 'rounded-tl-none bg-gray-700 text-white'
						}`}
					>
						<p class="whitespace-pre-wrap">{message.content}</p>
						<div class="mt-1 text-right text-xs opacity-70">
							{message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
						</div>
					</div>
				</div>
			{/each}
		</div>
	</div>

	<div
		class="animate-in fade-in-50 slide-in-from-bottom-2 flex flex-col overflow-hidden rounded-lg bg-gray-700 delay-100 duration-300"
	>
		<textarea
			class="w-full resize-none bg-transparent p-4 text-white placeholder-gray-400 focus:outline-none"
			placeholder="Ask the AI assistant..."
			rows="3"
			bind:value={inputMessage}
			onkeydown={handleKeydown}
		></textarea>

		<div class="flex items-center justify-between bg-gray-800 p-2">
			<div class="text-xs text-gray-400">Press Enter to send, Shift+Enter for new line</div>
			<button
				class="rounded-md bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
				onclick={sendMessage}
				disabled={!inputMessage.trim()}
			>
				Send
			</button>
		</div>
	</div>
</div>
