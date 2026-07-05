import { API_BASE_URL } from './apiConfig';

export interface GraphNode {
    id: string;
    label: string;
    type: string;
    data: Record<string, unknown>;
}

export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    type: string;
    data: Record<string, unknown>;
}

export interface GraphPayload {
    nodes: GraphNode[];
    edges: GraphEdge[];
    reflection?: string;
    summary?: string;
    discovery?: string;
    questions?: string[];
    notifications?: string[];
}

export async function fetchGraph(sessionId: string): Promise<GraphPayload> {
    const response = await fetch(`${API_BASE_URL}/api/graph?session_id=${encodeURIComponent(sessionId)}`);

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to fetch graph.');
    }

    return response.json() as Promise<GraphPayload>;
}
