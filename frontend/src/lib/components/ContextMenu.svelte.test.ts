import { render, screen, fireEvent } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';
import ContextMenu from './ContextMenu.svelte';
import type { ContextMenuItem } from './ContextMenu.svelte';
import Circle from 'phosphor-svelte/lib/Circle';

test('ContextMenu renders and interacts correctly', async () => {
    const user = userEvent.setup();
    const onCloseMock = vi.fn();
    const itemActionMock = vi.fn();

    const items: ContextMenuItem[] = [
        { label: 'Item 1', action: itemActionMock, iconComponent: Circle },
        { label: 'Item 2', action: () => { }, danger: true },
        { label: 'Item 3', action: () => { } }
    ];

    const { container, unmount } = render(ContextMenu, {
        props: {
            items,
            x: 100,
            y: 200,
            onClose: onCloseMock
        }
    });

    const contextMenuElement = container.querySelector('#context-menu');

    // 1. Renders with correct items and position
    expect(contextMenuElement).toBeInTheDocument();
    expect(contextMenuElement).toHaveStyle('left: 100px');
    expect(contextMenuElement).toHaveStyle('top: 200px');

    const menuButtons = screen.getAllByRole('button');
    expect(menuButtons).toHaveLength(items.length);
    expect(screen.getByText('Item 1')).toBeInTheDocument();

    // Check for the rendered SVG icon and its classes
    const iconElement = container.querySelector('svg');
    expect(iconElement).toBeInTheDocument();
    expect(iconElement).toHaveClass('mr-2');
    expect(iconElement).toHaveClass('h-4');
    expect(iconElement).toHaveClass('w-4');

    expect(screen.getByText('Item 2')).toBeInTheDocument();
    expect(screen.getByText('Item 3')).toBeInTheDocument();

    // 2. Item click triggers action and closes menu
    const firstItemButton = screen.getByText('Item 1');
    await user.click(firstItemButton);
    expect(itemActionMock).toHaveBeenCalledTimes(1);
    expect(onCloseMock).toHaveBeenCalledTimes(1);

    unmount();
    onCloseMock.mockClear();
    itemActionMock.mockClear();

    const { unmount: unmount2 } = render(ContextMenu, {
        props: {
            items,
            x: 100,
            y: 200,
            onClose: onCloseMock
        }
    });

    // 3. Clicking outside closes the menu
    await new Promise(resolve => setTimeout(resolve, 0));
    await fireEvent.mouseDown(document.body);
    expect(onCloseMock).toHaveBeenCalledTimes(1);

    unmount2();
    onCloseMock.mockClear();

    const { unmount: unmount3 } = render(ContextMenu, {
        props: {
            items,
            x: 100,
            y: 200,
            onClose: onCloseMock
        }
    });

    // 4. Danger item has correct styling
    const dangerItemButton = screen.getByText('Item 2');
    expect(dangerItemButton).toHaveClass('text-red-600');
    expect(dangerItemButton).toHaveClass('hover:text-red-700');

    const normalItemButton = screen.getByText('Item 3');
    expect(normalItemButton).toHaveClass('text-gray-700');
    expect(normalItemButton).not.toHaveClass('text-red-600');

    unmount3();
});
