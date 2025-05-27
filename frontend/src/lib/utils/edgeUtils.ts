import type { Node, Edge, Connection } from '@xyflow/svelte';
import { getColorForType } from '$lib/utils/colorUtils';

interface EdgeStyleProps {
	style: string;
	animated: boolean;
}

/**
 * Determines the style and animation properties for a Svelte Flow edge.
 *
 * @param sourceNode - The source node object.
 * @param edgeOrConnection - The edge or connection object.
 * @returns An object containing the style string and animated boolean.
 */
export function getEdgeStyleProps(
	sourceNode: Node | undefined,
	edgeOrConnection: Edge | Connection
): EdgeStyleProps {
	if (!sourceNode) {
		// Return default style if source node is not found
		return { style: 'stroke-width:3;', animated: false };
	}

	let taskId: string | undefined = undefined;

	// Determine the task type based on the source node and edge/connection handle
	if (edgeOrConnection.sourceHandle && edgeOrConnection.sourceHandle.startsWith('output-')) {
		// For worker nodes, the output handle determines the type
		taskId = edgeOrConnection.sourceHandle.substring(7); // remove 'output-' prefix
	}

	let styleString = 'stroke-width:3;'; // Default thickness
	if (taskId) {
		const color = getColorForType(taskId);
		styleString += `stroke:${color};`; // Add color if type found
	}

	// Edges originating from DataInput nodes are animated
	const animated = sourceNode.type === 'datainput';

	return {
		style: styleString,
		animated: animated
	};
}
