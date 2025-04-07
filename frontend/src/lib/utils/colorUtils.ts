import { schemeCategory10 } from 'd3-scale-chromatic';

// Use the imported color scheme directly
const category10Colors: readonly string[] = schemeCategory10;

/**
 * Creates a function that mimics d3.scaleOrdinal.
 * It assigns colors from the range to unique domain values as they are encountered.
 * @param range An array of colors (or other values) to assign.
 * @returns A function that takes a domain value (string) and returns a color.
 */
function createOrdinalScale(range: readonly string[]) {
    const domainMap = new Map<string, string>();
    let nextIndex = 0;

    return function (domainValue: string): string {
        if (domainMap.has(domainValue)) {
            return domainMap.get(domainValue)!;
        }

        const color = range[nextIndex % range.length];
        domainMap.set(domainValue, color);
        nextIndex++;
        return color;
    };
}

// Create our custom ordinal scale instance
const typeColorScale = createOrdinalScale(category10Colors);

/**
 * Generates a consistent color based on a string input (e.g., class name).
 * Uses a predefined color scheme (Category10) and cycles through it.
 * @param typeName The string identifier (e.g., class name) for the type.
 * @returns A hex color string.
 */
export function getColorForType(typeName: string): string {
    return typeColorScale(typeName);
}

/**
 * Calculates the vertical position for a handle based on its index and total count.
 * @param index The index of the handle (0-based).
 * @param total The total number of handles of that type (source or target).
 * @param nodeHeight The approximate height of the node section where handles are placed. Defaults to a reasonable value.
 * @returns A percentage string for the 'top' CSS property.
 */
export function calculateHandlePosition(index: number, total: number, nodeHeight: number = 100): string {
    if (total <= 0) return '50%'; // Default center if no handles somehow

    // Calculate spacing to distribute handles evenly, leaving some padding
    const totalSpacing = nodeHeight * 0.25; // Use 80% of height for handles
    const spacingPerHandle = total > 1 ? totalSpacing / (total - 1) : 0; // Avoid division by zero for single handle
    const startOffset = (nodeHeight - totalSpacing) / 2; // Center the block of handles vertically

    let topPositionPx = startOffset + (index * spacingPerHandle);

    // For a single handle, center it
    if (total === 1) {
        topPositionPx = nodeHeight / 2;
    }

    // Convert to percentage - Assuming the parent container's height corresponds somewhat to nodeHeight
    // This might need adjustment depending on the actual node layout.
    // A fixed pixel offset might be more reliable if percentage causes issues.
    // Let's try pixels first for more direct control.

    // Return pixel value for direct style application
    // The parent container needs relative positioning for this to work.
    return `${topPositionPx}px`;
} 