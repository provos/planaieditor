interface SplitePaneConfig {
    isOpen: boolean;
}

export const splitPaneConfig = $state<SplitePaneConfig>({
    isOpen: false,
});

export function openSplitPane() {
    splitPaneConfig.isOpen = true;
}

export function closeSplitPane() {
    splitPaneConfig.isOpen = false;
}

export function toggleSplitPane() {
    splitPaneConfig.isOpen = !splitPaneConfig.isOpen;
}