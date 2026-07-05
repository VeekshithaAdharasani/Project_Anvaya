import React, { useEffect, useMemo } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    ReactFlowProvider,
    useReactFlow,
    type Edge,
    type Node,
} from 'reactflow';
import 'reactflow/dist/style.css';
import '../styles/graph.css';

export type GraphViewNode = Node;

export type GraphViewEdge = Edge;

interface GraphViewProps {
    nodes?: GraphViewNode[];
    edges?: GraphViewEdge[];
    loading?: boolean;
    onNodeSelect?: (node: GraphViewNode | null) => void; // State callback added
}

const GraphViewInner: React.FC<GraphViewProps> = ({ 
    nodes = [], 
    edges = [], 
    loading = false,
    onNodeSelect
}) => {
    const { fitView } = useReactFlow();

    // Assign classes dynamically based on taxonomy category
    const flowNodes = useMemo<Node[]>(() => {
        return nodes.map((node) => {
            const category = (
                node.data?.category || 
                node.data?.type || 
                ''
            ).toString().toLowerCase().trim();

            const categoryClass = category ? `anvaya-node-${category}` : '';

            return {
                ...node,
                className: `anvaya-node ${categoryClass}`,
            };
        });
    }, [nodes]);

    const flowEdges = useMemo<Edge[]>(() => edges, [edges]);

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
                fitView
                fitViewOptions={{ padding: 0.2 }}
                proOptions={{ hideAttribution: true }}
                onNodeClick={(_event, node) => onNodeSelect?.(node)} // Handle selection
                onPaneClick={() => onNodeSelect?.(null)}             // Handle deselection
            >
                <Background gap={12} size={1} />
                <Controls />
                <MiniMap nodeStrokeColor="#E8E2D8" nodeColor="#FFFDF9" />
            </ReactFlow>

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