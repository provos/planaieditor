interface SplitePaneConfig {
	size: number;
	selectedNodeId: string | null;
	upperNodeType: 'tool' | 'task' | 'taskimport' | null;
	upperNodeId: string | null;
}

export const MAX_SPLIT_PANE_SIZE = 40;

export const splitPaneConfig = $state<SplitePaneConfig>({
	size: 0,
	selectedNodeId: null,
	upperNodeId: null,
	upperNodeType: null
});

export function openSplitPane() {
	splitPaneConfig.size = MAX_SPLIT_PANE_SIZE;
}

export function isSplitPaneOpen() {
	return splitPaneConfig.size > 0;
}

export function closeSplitPane() {
	splitPaneConfig.size = 0;
}

export function toggleSplitPane() {
	splitPaneConfig.size = splitPaneConfig.size === 0 ? MAX_SPLIT_PANE_SIZE : 0;
}
