import type { Node, Edge, Connection } from '@xyflow/svelte';
import { getColorForType } from '$lib/utils/colorUtils';
import type { NodeData } from '$lib/components/nodes/TaskNode.svelte'; // Assuming TaskNode exports its data type

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

	let taskType: string | undefined = undefined;
	const isTaskSource = sourceNode.type === 'datainput';

	// Determine the task type based on the source node and edge/connection handle
	if (isTaskSource) {
		// The class name defines the type
		taskType = (sourceNode.data as unknown as NodeData)?.className;
	} else if (edgeOrConnection.sourceHandle && edgeOrConnection.sourceHandle.startsWith('output-')) {
		// For worker nodes, the output handle determines the type
		taskType = edgeOrConnection.sourceHandle.split('-')[1];
	} else if (
		// Fallback for workers with a single output type declared in data
		sourceNode.data &&
		Array.isArray(sourceNode.data.output_types) &&
		sourceNode.data.output_types.length === 1
	) {
		taskType = sourceNode.data.output_types[0];
	}

	let styleString = 'stroke-width:3;'; // Default thickness
	if (taskType) {
		const color = getColorForType(taskType);
		styleString += `stroke:${color};`; // Add color if type found
	}

	// Edges originating from DataInput nodes are animated
	const animated = isTaskSource;

	return {
		style: styleString,
		animated: animated
	};
}
