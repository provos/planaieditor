<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import DotsThreeVertical from 'phosphor-svelte/lib/DotsThreeVertical';
	import CaretRight from 'phosphor-svelte/lib/CaretRight';
	import List from 'phosphor-svelte/lib/List';
	import Info from 'phosphor-svelte/lib/Info';
	import simpleIOExample from '$lib/examples/simple-input-output.json';
	import simpleTopicExtraction from '$lib/examples/simple-topic-extraction.json';
	import availableDomains from '$lib/examples/available-domains.json';
	import AboutModal from './AboutModal.svelte';

	const { onLoadJSON }: { onLoadJSON: (data: any) => void } = $props();

	let showAboutModal = $state(false);

	function openAbout() {
		showAboutModal = true;
	}

	function closeAbout() {
		showAboutModal = false;
	}
</script>

<DropdownMenu.Root>
	<DropdownMenu.Trigger
		class="flex h-10 w-10 items-center justify-center rounded-md text-gray-600 transition-colors hover:bg-gray-200 hover:text-gray-800 focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 focus:outline-none"
		aria-label="Examples Menu"
	>
		<DotsThreeVertical size={20} weight="bold" />
	</DropdownMenu.Trigger>
	<DropdownMenu.Portal>
		<DropdownMenu.Content
			class="z-50 w-48 rounded-md border border-gray-200 bg-white p-1 shadow-xl focus:outline-none"
			sideOffset={5}
		>
			<DropdownMenu.Sub>
				<DropdownMenu.SubTrigger
					class="flex h-8 w-full cursor-default items-center rounded-sm px-2 py-1.5 text-sm outline-none select-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[highlighted]:bg-gray-100 data-[state=open]:bg-gray-100"
				>
					<List size={18} class="mr-2 text-gray-500" />
					Examples
					<div class="ml-auto">
						<CaretRight class="h-4 w-4" />
					</div>
				</DropdownMenu.SubTrigger>
				<DropdownMenu.SubContent
					class="z-50 w-64 rounded-md border border-gray-200 bg-white p-1 shadow-xl focus:outline-none"
					sideOffset={2}
					alignOffset={-5}
				>
					<DropdownMenu.Item
						class="relative flex h-8 cursor-default items-center rounded-sm px-2 py-1.5 pl-8 text-sm outline-none select-none hover:bg-gray-100 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[highlighted]:bg-gray-100"
						onSelect={() => {
							onLoadJSON(JSON.stringify(simpleIOExample));
						}}
					>
						Simple Input/Output
					</DropdownMenu.Item>
					<DropdownMenu.Item
						class="relative flex h-8 cursor-default items-center rounded-sm px-2 py-1.5 pl-8 text-sm outline-none select-none hover:bg-gray-100 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[highlighted]:bg-gray-100"
						onSelect={() => {
							onLoadJSON(JSON.stringify(simpleTopicExtraction));
						}}
					>
						Simple Page Topic Extraction
					</DropdownMenu.Item>
					<DropdownMenu.Item
						class="relative flex h-8 cursor-default items-center rounded-sm px-2 py-1.5 pl-8 text-sm outline-none select-none hover:bg-gray-100 data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[highlighted]:bg-gray-100"
						onSelect={() => {
							onLoadJSON(JSON.stringify(availableDomains));
						}}
					>
						Assistant For Available Domains
					</DropdownMenu.Item>
				</DropdownMenu.SubContent>
			</DropdownMenu.Sub>
			<DropdownMenu.Separator class="my-1 h-px bg-gray-200" />
			<DropdownMenu.Item
				class="flex h-8 w-full cursor-default items-center rounded-sm px-2 py-1.5 text-sm outline-none select-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[highlighted]:bg-gray-100"
				onSelect={openAbout}
			>
				<Info size={18} class="mr-2 text-gray-500" />
				About
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</DropdownMenu.Portal>
</DropdownMenu.Root>

<AboutModal show={showAboutModal} onClose={closeAbout} />
