<script lang="ts">
	import { X, Eraser, CircleNotch } from 'phosphor-svelte';
	import {
		closeAssistant,
		assistantState,
		assistantResponse,
		assistantMessages,
		clearAssistantMessages
	} from '$lib/stores/assistantStateStore.svelte';
	import { useSvelteFlow, type Node, type Edge } from '@xyflow/svelte';
	import type { DataInputNodeData } from '$lib/components/nodes/DataInputNode.svelte';
	import { onMount } from 'svelte';
	import { findDataInputForAssistant } from '$lib/utils/nodeUtils';
	import { socketStore } from '$lib/stores/socketStore.svelte';
	import { exportPythonCode } from '$lib/utils/pythonExport';
	import { tick } from 'svelte';
	import { marked } from 'marked';
	import { get } from 'svelte/store';
	import { escapeHtml } from '$lib/utils/utils';
	import { graphName } from '$lib/stores/graphNameStore.svelte';

	let inputMessage: string = $state('');
	let chatContainer: HTMLElement;

	let { getNodes, getEdges } = useSvelteFlow();

	onMount(() => {
		// validate that the messages follow the interface
		assistantMessages.subscribe((currentMessages) => {
			if (currentMessages.length) {
				let isValid = true;
				for (const message of currentMessages) {
					if (
						!message ||
						(message.type !== 'user' && message.type !== 'assistant') ||
						typeof message.content !== 'string' ||
						message.content.trim() === '' ||
						!(message.timestamp instanceof Date)
					) {
						isValid = false;
						break;
					}
				}
				if (!isValid) {
					console.error('Invalid messages in assistant mode. Clearing messages.');
					assistantMessages.set([]);
				}
			}
		})();
	});

	function sendMessage() {
		if (!inputMessage.trim()) return;

		const userQuery = inputMessage;

		assistantMessages.update((currentMessages) => [
			...currentMessages,
			{
				type: 'user',
				content: userQuery,
				timestamp: new Date()
			}
		]);
		inputMessage = '';

		const currentFlowNodes = getNodes();
		const targetNode = findDataInputForAssistant(currentFlowNodes);

		if (targetNode) {
			const currentMessages = get(assistantMessages);
			const transformedMessages = currentMessages.map((message) => ({
				role: message.type === 'user' ? 'user' : 'assistant',
				content: message.content
			}));
			const chatTaskPayload = {
				messages: transformedMessages
			};
			const jsonDataString = JSON.stringify(chatTaskPayload, null, 2);

			const nodesFromFlow = getNodes();
			const nodesForExport: Node[] = nodesFromFlow.map((node) => {
				if (node.id === targetNode.id) {
					return {
						...node,
						data: {
							...node.data,
							jsonData: jsonDataString,
							isJsonValid: true // Assume valid as we constructed it
						} as DataInputNodeData as any
					};
				}
				return node;
			});

			const edgesForExport: Edge[] = getEdges();

			if (socketStore.socket && socketStore.isConnected) {
				exportPythonCode(socketStore.socket, nodesForExport, edgesForExport, 'execute');
				assistantState.isRunning = true;
			} else {
				console.error('Socket not connected, cannot execute.');
				assistantMessages.update((currentMessages) => [
					...currentMessages,
					{
						type: 'assistant',
						content:
							'Error: Could not connect to the backend to process your request. Please check the connection.',
						timestamp: new Date()
					}
				]);
				assistantState.isRunning = false;
			}
		} else {
			console.warn('No suitable DataInputNode found for ChatTask or assistant.');
			assistantMessages.update((currentMessages) => [
				...currentMessages,
				{
					type: 'assistant',
					content:
						"I'm not properly configured to process this request. A 'ChatTask' DataInput node is required.",
					timestamp: new Date()
				}
			]);
			assistantState.isRunning = false;
		}
	}

	function handleNewChat() {
		clearAssistantMessages();
		inputMessage = '';
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
		const unsubscribe = assistantMessages.subscribe((currentMessagesVal) => {
			if (currentMessagesVal.length) {
				tick().then(scrollToBottom);
			}
		});
		return unsubscribe;
	});

	$effect(() => {
		const unsubscribe = assistantResponse.subscribe((responseContent) => {
			if (responseContent) {
				assistantMessages.update((currentMessages) => [
					...currentMessages,
					{
						type: 'assistant',
						content: responseContent,
						timestamp: new Date()
					}
				]);
				assistantResponse.set(null);
			}
		});

		return () => {
			unsubscribe();
		};
	});
</script>

<div
	class="animate-in fade-in-0 slide-in-from-bottom-5 fixed inset-0 z-50 flex flex-col bg-gray-900/95 p-4 backdrop-blur-sm duration-200"
>
	<div class="mb-4 flex items-center justify-between">
		<div class="flex items-baseline">
			<h2 class="text-xl font-semibold text-white">Assistant Mode</h2>
			{#if $graphName}
				<span class="ml-2 text-sm text-gray-400">({$graphName})</span>
			{/if}
		</div>
		<div>
			<button
				class="mr-2 rounded-full p-2 text-gray-300 transition-colors hover:bg-gray-700 hover:text-white"
				onclick={handleNewChat}
				title="New Chat"
			>
				<Eraser size={22} weight="bold" />
			</button>
			<button
				class="rounded-full p-2 text-gray-300 transition-colors hover:bg-gray-700 hover:text-white"
				onclick={closeAssistant}
				title="Close Assistant"
			>
				<X size={24} weight="bold" />
			</button>
		</div>
	</div>

	<div
		class="scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-transparent mb-4 flex-1 overflow-y-auto pr-2"
		bind:this={chatContainer}
	>
		<div class="flex flex-col space-y-4">
			{#each $assistantMessages as message, i (i)}
				<div
					class={`flex ${message.type === 'user' ? 'justify-end' : 'justify-center'} animate-in fade-in-50 slide-in-from-${message.type === 'user' ? 'right' : 'left'}-5 duration-200`}
				>
					<div
						class={`rounded-lg p-3 ${
							message.type === 'user'
								? 'max-w-[80%] rounded-tr-none bg-blue-600 text-white'
								: 'prose prose-invert prose-md w-full max-w-6xl rounded-tl-none bg-gray-700 text-white'
						}`}
					>
						{#if message.type === 'assistant'}
							{@html marked.parse(escapeHtml(message.content))}
						{:else}
							<p class="whitespace-pre-wrap">{message.content}</p>
						{/if}
						<div class="mt-1 text-right text-xs opacity-70">
							{message.timestamp && message.timestamp instanceof Date
								? message.timestamp.toLocaleTimeString([], {
										hour: '2-digit',
										minute: '2-digit'
									})
								: ''}
						</div>
					</div>
				</div>
			{/each}
			{#if assistantState.isRunning}
				<div class="animate-in fade-in-50 slide-in-from-left-5 flex justify-center duration-200">
					<div
						class="prose prose-invert prose-md inline-flex w-full max-w-6xl rounded-tl-none text-white"
					>
						<CircleNotch size={20} class="mr-2 animate-spin" />
						Thinking...
					</div>
				</div>
			{/if}
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
			{#if assistantState.isRunning}
				<div class="flex items-center justify-center px-4 py-2 text-white">
					<CircleNotch size={24} class="animate-spin" />
				</div>
			{:else}
				<button
					class="rounded-md bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
					onclick={sendMessage}
					disabled={!inputMessage.trim() || assistantState.isRunning}
				>
					Send
				</button>
			{/if}
		</div>
	</div>
</div>
