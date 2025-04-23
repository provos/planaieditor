export function formatErrorMessage(errorText: string): string {
    if (!errorText) return '';

    // First escape HTML special characters to prevent XSS
    const escaped = errorText
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');

    // Then replace newlines with <br> tags
    return escaped.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');
}

// Debounce function to prevent excessive calls to the server
export function debounce(func: Function, wait: number) {
    let timeout: number | undefined;
    return function executedFunction(...args: any[]) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}