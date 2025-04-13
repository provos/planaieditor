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