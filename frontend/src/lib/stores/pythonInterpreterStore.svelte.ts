// Store for the currently selected Python interpreter path
export const selectedInterpreterPath = $state<{
    value: string | null;
}>({
    value: null,
});