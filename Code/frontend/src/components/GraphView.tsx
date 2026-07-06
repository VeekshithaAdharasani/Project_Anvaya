import React, { useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  useReactFlow,
  Handle,
  Position,
  MarkerType,
  type Edge,
  type Node,
  type NodeTypes,
  type NodeProps,
} from "reactflow";
import 'reactflow/dist/style.css';
import '../styles/graph.css';

export type GraphViewNode = Node;
export type GraphViewEdge = Edge;

interface GraphViewProps {
    nodes?: GraphViewNode[];
    edges?: GraphViewEdge[];
    loading?: boolean;
    onNodeSelect?: (node: GraphViewNode | null) => void;
}

// ==========================================
// CONFIGURABLE TIER LAYOUT CONSTANTS
// ==========================================

const TIER_ORDER: Record<string, number> = {
    'dreams': 0,
    'dream': 0,
    'motivations': 0,
    'motivation': 0,
    
    'goals': 1,
    'goal': 1,
    
    'skills': 2,
    'skill': 2,
    'learning': 2,
    
    'projects': 3,
    'project': 3,
    
    'values': 4,
    'value': 4,
    'traits': 4,
    'trait': 4,
    
    'interests': 5,
    'interest': 5,
};

const DEFAULT_TIER_INDEX = 2;

const BASE_X_SPACING = 210;
const BASE_Y_SPACING = 95;
const BASE_SUB_ROW_GAP = 40;

const EXCLUDED_CATEGORIES = new Set(['confidence', 'reflection', 'reflections']);

// Helper: Horizontal slot positioning calculator
const getAlternatingSlot = (index: number): number => {
    if (index === 0) return 0;
    const sign = index % 2 === 1 ? 1 : -1;
    return sign * Math.ceil(index / 2);
};

// ==========================================
// CATEGORY-SPECIFIC SVG ICONS FOR CUSTOM NODES
// ==========================================

const getCategoryIcon = (category: string) => {
    const strokeWidth = 2.2;
    const size = 14;
    
    switch (category) {
        case 'goals':
        case 'goal':
            return (
                <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <circle cx="12" cy="12" r="6" />
                    <circle cx="12" cy="12" r="2" />
                </svg>
            );
        case 'skills':
        case 'skill':
        case 'learning':
            return (
                <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                    <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                </svg>
            );
        case 'projects':
        case 'project':
            return (
                <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="16 18 22 12 16 6" />
                    <polyline points="8 6 2 12 8 18" />
                </svg>
            );
        case 'interests':
        case 'interest':
            return (
                <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                </svg>
            );
        case 'dreams':
        case 'dream':
        case 'motivations':
        case 'motivation':
            return (
                <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707.707M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />
                </svg>
            );
        default:
            return (
                <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
            );
    }
};

// ==========================================
// CUSTOM PREMIUM NODE COMPONENT
// ==========================================

const AnvayaNodeComponent: React.FC<NodeProps> = ({ data, selected }) => {
    const rawCategory = data.category || data.type || '';
    const categoryStr = rawCategory.toString().trim();
    
    // Display the category only if it is a genuine, non-generic identifier
    const displayCategory = categoryStr.toLowerCase() !== 'concept' ? categoryStr : '';
    const categoryLower = categoryStr.toLowerCase().trim();

    return (
        <div className={`anvaya-custom-node-card ${selected ? 'selected' : ''}`}>
            <Handle type="target" position={Position.Top} style={{ background: 'transparent', border: 'none' }} />
            
            <div className="anvaya-node-card-body">
                <div className={`anvaya-node-icon-wrapper anvaya-node-icon-${categoryLower}`}>
                    {getCategoryIcon(categoryLower)}
                </div>
                
                <div className="anvaya-node-details">
                    <span className="anvaya-node-title">{data.label}</span>
                    {displayCategory && (
                        <div className="anvaya-node-meta-row">
                            <span className={`anvaya-node-category-pill anvaya-category-pill-${categoryLower}`}>
                                {displayCategory}
                            </span>
                        </div>
                    )}
                </div>
            </div>

            <Handle type="source" position={Position.Bottom} style={{ background: 'transparent', border: 'none' }} />
        </div>
    );
};

// ==========================================
// CORE COMPONENT IMPLEMENTATION
// ==========================================

const GraphViewInner: React.FC<GraphViewProps> = ({ 
    nodes = [], 
    edges = [], 
    loading = false,
    onNodeSelect
}) => {
    const { fitView } = useReactFlow();
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

    // Register our custom Premium Card Node as the default type
    const nodeTypes: NodeTypes = useMemo(
        () => ({
            default: AnvayaNodeComponent,
        }),
        []
    );

    // Selection Network: Calculate connected node and edge IDs dynamically
    const connectedNodeIds = useMemo(() => {
        if (!selectedNodeId) return new Set<string>();
        const connected = new Set<string>([selectedNodeId]);
        edges.forEach((edge) => {
            if (edge.source === selectedNodeId) {
                connected.add(edge.target);
            }
            if (edge.target === selectedNodeId) {
                connected.add(edge.source);
            }
        });
        return connected;
    }, [selectedNodeId, edges]);

    const connectedEdgeIds = useMemo(() => {
        if (!selectedNodeId) return new Set<string>();
        const connected = new Set<string>();
        edges.forEach((edge) => {
            if (edge.source === selectedNodeId || edge.target === selectedNodeId) {
                connected.add(edge.id);
            }
        });
        return connected;
    }, [selectedNodeId, edges]);

    // 1. Arrange nodes into horizontally compact, wrapped semantic tiers
    const flowNodes = useMemo<Node[]>(() => {
        // Step A: Filter out metadata categories
        const filtered = nodes.filter((node) => {
            const category = (
                node.data?.category ??
                node.data?.type ??
                node.data?.node_type ??
                ''
            ).toString().toLowerCase().trim();
            return !EXCLUDED_CATEGORIES.has(category);
        });

        // Step B: Calculate scaling metrics based on node counts to ensure full panel fit
        const totalNodesCount = filtered.length;
        const scaleFactor = totalNodesCount > 14 ? 0.75 : totalNodesCount > 8 ? 0.85 : 1.0;

        const X_SPACING = BASE_X_SPACING * scaleFactor;
        const Y_SPACING = BASE_Y_SPACING * scaleFactor;
        const SUB_ROW_GAP = BASE_SUB_ROW_GAP * scaleFactor;

        // Step C: Count node connectivity degree to position central hubs
        const degrees: Record<string, number> = {};
        filtered.forEach((node) => {
            degrees[node.id] = 0;
        });
        edges.forEach((edge) => {
            if (degrees[edge.source] !== undefined) degrees[edge.source]++;
            if (degrees[edge.target] !== undefined) degrees[edge.target]++;
        });

        // Step D: Group nodes into their respective tier rows
        const tierGroups: Record<number, Node[]> = {};
        filtered.forEach((node) => {
            const category = (
                node.data?.category ??
                node.data?.type ??
                node.data?.node_type ??
                ''
            ).toString().toLowerCase().trim();

            const tierIndex = TIER_ORDER[category] ?? DEFAULT_TIER_INDEX;
            if (!tierGroups[tierIndex]) {
                tierGroups[tierIndex] = [];
            }
            tierGroups[tierIndex].push(node);
        });

        // Step E: Render centered tiers, wrapping large groups into balanced sub-row grids
        return filtered.map((node) => {
            const category = (
                node.data?.category ??
                node.data?.type ??
                node.data?.node_type ??
                ''
            ).toString().toLowerCase().trim();

            const tierIndex = TIER_ORDER[category] ?? DEFAULT_TIER_INDEX;
            const group = tierGroups[tierIndex] ?? [];
            const N_t = group.length;

            // Sort stably by degree (descending) then alphabetically by label to keep hubs in the center
            const sortedGroup = [...group].sort((a, b) => {
                const degA = degrees[a.id] ?? 0;
                const degB = degrees[b.id] ?? 0;
                if (degB !== degA) return degB - degA;
                
                const labelA = (a.data?.label ?? a.id).toString();
                const labelB = (b.data?.label ?? b.id).toString();
                return labelA.localeCompare(labelB);
            });

            const index = sortedGroup.findIndex((n) => n.id === node.id);

            let x = 0;
            let yOffset = 0;

            // Wrap large tiers into a beautiful, compact 2D grid of sub-rows
            if (N_t > 3) {
                const subRowIndex = index % 2; // 0 = upper sub-row, 1 = lower sub-row
                const colIndex = Math.floor(index / 2);
                const slotX = getAlternatingSlot(colIndex);

                x = slotX * X_SPACING;
                yOffset = (subRowIndex === 0 ? -1 : 1) * SUB_ROW_GAP;
            } else {
                const slotX = getAlternatingSlot(index);
                x = slotX * X_SPACING;
                yOffset = 0;
            }

            const y = (tierIndex * Y_SPACING) + yOffset;
            const categoryClass = category ? `anvaya-node-${category}` : '';

            // Apply interaction fading classes dynamically
            let interactionClass = '';
            if (selectedNodeId) {
                if (node.id === selectedNodeId) {
                    interactionClass = 'selected';
                } else if (connectedNodeIds.has(node.id)) {
                    interactionClass = 'anvaya-node-connected';
                } else {
                    interactionClass = 'anvaya-node-faded';
                }
            }

            return {
                ...node,
                position: { x, y },
                className: `anvaya-node ${categoryClass} ${interactionClass}`,
            };
        });
    }, [nodes, edges, selectedNodeId, connectedNodeIds]);

    // 2. Remove edge labels, apply relationship colors and arrows, and handle fade interactions
    const flowEdges = useMemo<Edge[]>(() => {
        const activeNodeIds = new Set(flowNodes.map((n) => n.id));

        return edges
            .filter((edge) => activeNodeIds.has(edge.source) && activeNodeIds.has(edge.target))
            .map((edge) => {
                const relationship = (
                    edge.label ??
                    edge.data?.relationship ??
                    edge.data?.relationship_type ??
                    edge.data?.type ??
                    edge.data?.label ??
                    'related_to'
                ).toString().toLowerCase().trim();

                // Select distinct warm color based on the semantic relationship type
                let edgeColor = '#D4A373'; // Fallback: Supports (Amber Gold)
                
                if (relationship.includes('lead')) {
                    edgeColor = '#7C5CFC'; // Leads to (Indigo)
                } else if (relationship.includes('related')) {
                    edgeColor = '#6CA6CD'; // Related to (Blue)
                } else if (relationship.includes('inspire')) {
                    edgeColor = '#F0A5C2'; // Inspired by (Rose)
                } else if (relationship.includes('depend')) {
                    edgeColor = '#E29B7A'; // Depends on (Terracotta)
                }

                // Apply interactive faded classes based on selection network state
                let edgeClass = '';
                if (selectedNodeId) {
                    edgeClass = connectedEdgeIds.has(edge.id) ? 'anvaya-edge-connected' : 'anvaya-edge-faded';
                }

                return {
                    ...edge,
                    label: undefined, // Omitted to clear graph text overlay clutter
                    className: edgeClass,
                    style: {
                        stroke: edgeColor,
                        strokeWidth: selectedNodeId && connectedEdgeIds.has(edge.id) ? 3 : 2,
                    },
                    markerEnd: {
                        type: MarkerType.ArrowClosed,
                        color: edgeColor,
                        width: 14,
                        height: 14,
                    },
                };
            });
    }, [edges, flowNodes, selectedNodeId, connectedEdgeIds]);

    useEffect(() => {
        if (!loading && flowNodes.length > 0) {
            fitView({ padding: 0.2, duration: 200 });
        }
    }, [fitView, flowNodes, flowEdges, loading]);

    const hasGraphData = flowNodes.length > 0 || flowEdges.length > 0;

    return (
        <div className="graph-view-canvas-wrapper">
            <ReactFlow
                nodes={flowNodes}
                edges={flowEdges}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                proOptions={{ hideAttribution: true }}
                onNodeClick={(_event, node) => {
                    setSelectedNodeId(node.id);
                    onNodeSelect?.(node);
                }}
                onPaneClick={() => {
                    setSelectedNodeId(null);
                    onNodeSelect?.(null);
                }}
            >
                <Background gap={12} size={1} />
                <Controls />
                <MiniMap nodeStrokeColor="#E8E2D8" nodeColor="#FFFDF9" />
            </ReactFlow>

            {/* Floating Minimal Relationship Legend */}
            {hasGraphData && (
                <div className="anvaya-graph-legend">
                    <h6 className="anvaya-legend-title">Relationships</h6>
                    <div className="anvaya-legend-items">
                        <div className="anvaya-legend-item">
                            <span className="anvaya-legend-color-line" style={{ backgroundColor: '#D4A373' }}></span>
                            <span>Supports</span>
                        </div>
                        <div className="anvaya-legend-item">
                            <span className="anvaya-legend-color-line" style={{ backgroundColor: '#7C5CFC' }}></span>
                            <span>Leads to</span>
                        </div>
                        <div className="anvaya-legend-item">
                            <span className="anvaya-legend-color-line" style={{ backgroundColor: '#6CA6CD' }}></span>
                            <span>Related to</span>
                        </div>
                    </div>
                </div>
            )}

            {!hasGraphData && !loading && (
                <div className="graph-empty-state-pane">
                    <span className="graph-empty-icon" role="img" aria-label="sprout">🌱</span>
                    <h4 className="graph-empty-title">Your understanding map is waiting.</h4>
                    <p className="graph-empty-text">
                        Every meaningful conversation creates new connections.
                    </p>
                </div>
            )}
        </div>
    );
};

const GraphView: React.FC<GraphViewProps> = (props) => (
    <ReactFlowProvider>
        <GraphViewInner {...props} />
    </ReactFlowProvider>
);

export default GraphView;