export type SupportedLanguage = 'python' | 'markdown' | 'json' | 'javascript' | 'typescript';

interface FullScreenEditorState {
    id: string | undefined;
    isOpen: boolean;
    language: SupportedLanguage;
    _onSave?: (newCode: string) => void;
    _onClose?: () => void;
}

export const fullScreenEditorState = $state<FullScreenEditorState>({
    id: undefined,
    isOpen: false,
    language: 'python',
    _onSave: undefined,
    _onClose: undefined
});

export function openFullScreenEditor(
    id: string,
    language: SupportedLanguage = 'python',
    onSave: (newCode: string) => void = () => {},
    onClose: () => void = () => {}
) {
    fullScreenEditorState.id = id;
    fullScreenEditorState.language = language;
    fullScreenEditorState._onSave = onSave;
    fullScreenEditorState._onClose = onClose;
    fullScreenEditorState.isOpen = true;
}

export function closeFullScreenEditorStore() {
    if (fullScreenEditorState._onClose) {
        fullScreenEditorState._onClose();
    }
    fullScreenEditorState.isOpen = false;
    // Reset to defaults to avoid stale callbacks if not properly handled by caller
    fullScreenEditorState._onSave = undefined;
    fullScreenEditorState._onClose = undefined;
}

export function saveFullScreenEditor(newCode: string) {
    if (fullScreenEditorState._onSave) {
        fullScreenEditorState._onSave(newCode);
    }
    // Assuming save also implies closing. If not, the callback should handle it.
    fullScreenEditorState.isOpen = false;
    // Reset to defaults
    fullScreenEditorState._onSave = undefined;
    fullScreenEditorState._onClose = undefined;
}