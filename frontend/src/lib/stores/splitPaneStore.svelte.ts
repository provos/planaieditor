interface SplitePaneConfig {
    size: number;
    selectedNodeId: string | null;
}

export const splitPaneConfig = $state<SplitePaneConfig>({
    size: 0,
    selectedNodeId: null,
});

export function openSplitPane() {
    splitPaneConfig.size = 25;
}

export function closeSplitPane() {
    splitPaneConfig.size = 0;
}

export function toggleSplitPane() {
    splitPaneConfig.size = splitPaneConfig.size === 0 ? 25 : 0;
}