import Robot from 'phosphor-svelte/lib/Robot';
import Brain from 'phosphor-svelte/lib/Brain';
import ArrowsIn from 'phosphor-svelte/lib/ArrowsIn';
import Chat from 'phosphor-svelte/lib/Chat';
import Network from 'phosphor-svelte/lib/Network';
import Placeholder from 'phosphor-svelte/lib/Placeholder';
import Keyboard from 'phosphor-svelte/lib/Keyboard';
import Table from 'phosphor-svelte/lib/Table';
import Cube from 'phosphor-svelte/lib/Cube';
import FileMagnifyingGlass from 'phosphor-svelte/lib/FileMagnifyingGlass';
import Package from 'phosphor-svelte/lib/Package';
import Wrench from 'phosphor-svelte/lib/Wrench';
import type { Component } from 'svelte';
/**
 * Provides default code snippets for optional PlanAI TaskWorker methods.
 */

export function getDefaultMethodBody(methodName: string): string {
	switch (methodName) {
		case 'pre_consume_work':
			return `def pre_consume_work(self, task):
    """Optional: Prepare before consuming work."""
    # Your pre-processing logic here
    pass`;

		case 'post_consume_work':
			return `def post_consume_work(self, task):
    """Optional: Clean up after consuming work."""
    # Your post-processing logic here
    pass`;

		case 'extra_validation':
			return `def extra_validation(self, response: Task, input_task: Task) -> Optional[str]:
    """Optional: Validate the LLM response."""
    # Return an error string if validation fails, otherwise None
    return None`;

		case 'format_prompt':
			return `def format_prompt(self, task: Task) -> str:
    """Optional: Dynamically format the prompt based on the input task."""
    return self.prompt # Default implementation`;

		case 'pre_process':
			return `def pre_process(self, task: Task) -> Optional[Task]:
    """Optional: Pre-process the input task before LLM interaction."""
    # Return None to skip LLM call for this task
    return task`;

		case 'post_process':
			return `def post_process(self, response: Optional[Task], input_task: Task):
    """Optional: Post-process the LLM response before publishing."""
    # Process the response, potentially publishing different tasks
    if response:
        self.publish_work(response, input_task=input_task)`;

		case 'extra_cache_key':
			return `def extra_cache_key(self, task) -> Optional[str]:
    """Optional: Provide an extra key component for caching based on the task."""
    # Return a string or object that uniquely identifies the task variant
    return None`;

		default:
			return `# Default implementation for ${methodName}\npass`;
	}
}

export interface TaskWorkerStyle {
	icon: Component;
	color: string; // Tailwind CSS color class
}

const defaultTaskWorkerIcons: Record<string, TaskWorkerStyle> = {
	taskworker: { icon: Robot, color: 'text-purple-500' },
	llmtaskworker: { icon: Brain, color: 'text-green-500' },
	joinedtaskworker: { icon: ArrowsIn, color: 'text-orange-500' },
	subgraphworker: { icon: Network, color: 'text-teal-500' },
	chattaskworker: { icon: Chat, color: 'text-red-500' },
	datainput: { icon: Keyboard, color: 'text-gray-500' },
	assistantinput: { icon: Robot, color: 'text-purple-500' },
	dataoutput: { icon: Table, color: 'text-pink-500' },
	task: { icon: Cube, color: 'text-blue-500' },
	taskimport: { icon: FileMagnifyingGlass, color: 'text-cyan-500' },
	modulelevelimport: { icon: Package, color: 'text-emerald-500' },
	tool: { icon: Wrench, color: 'text-yellow-500' },
	default: { icon: Placeholder, color: 'text-gray-400' } // Default style
};

export function getNodeIconStyle(nodeTypeName: string): TaskWorkerStyle {
	return defaultTaskWorkerIcons[nodeTypeName.toLowerCase()] || defaultTaskWorkerIcons.default;
}
