import { useCallback, useEffect, useMemo, useState } from 'react';
import GraphView, { type GraphViewEdge, type GraphViewNode } from './components/GraphView';
import ChatPanel from './components/ChatPanel';
import { Dashboard } from './components/layouts/Dashboard';
import { ChapterDetails } from './components/journal/ChapterDetails';
import { DiscoveryCard } from './components/journal/DiscoveryCard';
import { QuestionsCard, type QuestionItem } from './components/journal/QuestionsCard';
import { fetchGraph, type GraphPayload } from './services/graphService';
import { StoryOfUnderstanding } from './components/journal/StoryOfUnderstanding';

// Stylesheets
import './styles/theme.css';
import './styles/layout.css';
import './styles/cards.css';

const DEFAULT_SESSION_ID = 'demo-session';

// Safely extend API definition for both Reflection & Curiosity Agents
interface ExtendedGraphPayload extends GraphPayload {
    reflection?: string;
    summary?: string;
    discovery?: string;
    questions?: string[] | QuestionItem[]; // Curiosity prompts
}

function App() {
    const [sessionId] = useState(DEFAULT_SESSION_ID);
    const [nodes, setNodes] = useState<GraphViewNode[]>([]);
    const [edges, setEdges] = useState<GraphViewEdge[]>([]);
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState('');

    // Core state management and concept bindings
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
    const [discoveryText, setDiscoveryText] = useState<string>('');
    const [discovery, setDiscovery] = useState<any>(null);
    const [storyEvents, setStoryEvents] = useState<any[]>([]);
    const [questions, setQuestions] = useState<QuestionItem[]>([]);

    // 1. Derived State: Bind active selected node data references dynamically
    const selectedNode = useMemo(() => {
        if (!selectedNodeId) return null;
        return nodes.find((node) => node.id === selectedNodeId) || null;
    }, [nodes, selectedNodeId]);

    // 2. Future-Proofed Selector: Compute contextual node queries or general fallbacks
    const activeQuestions = useMemo(() => {
        if (selectedNodeId) {
            // Retrieve contextual prompts aligned with active concept
            const contextual = questions.filter((q) => q.conceptId === selectedNodeId);
            if (contextual.length > 0) return contextual;
        }
        // Fall back to general prompts containing no specific conceptId associations
        return questions.filter((q) => !q.conceptId);
    }, [questions, selectedNodeId]);

    const loadGraph = useCallback(async () => {
        setLoading(true);
        try {
            const payload = (await fetchGraph(sessionId)) as any;
            const rawNodes =
                payload.nodes ??
                payload.graph?.nodes ??
                [];

            setNodes(
                rawNodes.map((node: any, index: number) => ({
                    id: node.id,
                    type: "default",
                    position: {
                        x: (index % 4) * 180,
                        y: Math.floor(index / 4) * 120,
                    },
                    data: {
                        label: node.name ?? node.label ?? node.data?.label ?? node.data?.name,
                        category: node.node_type ?? node.category ?? node.data?.category ?? node.data?.node_type ?? node.data?.type,
                        description: node.description ?? node.data?.description,
                        confidence: node.confidence ?? node.data?.confidence,
                        validation_status: node.validation_status ?? node.data?.validation_status,
                        evidence: node.evidence ?? node.data?.evidence,
                        created_at: node.created_at ?? node.data?.created_at,
                        updated_at: node.updated_at ?? node.data?.updated_at,
                    },
                }))
            );
            const rawEdges =
                payload.relationships ??
                payload.edges ??
                payload.graph?.relationships ??
                payload.graph?.edges ??
                [];

            setEdges(
                rawEdges.map((edge: any) => ({
                    id: edge.id,
                    source: edge.source_id ?? edge.source,
                    target: edge.target_id ?? edge.target,
                    type: 'default',
                    data: {
                        relationship_type: edge.relationship_type,
                        confidence: edge.confidence,
                        evidence: edge.evidence,
                    },
                })),
            );
            setStatus('Graph loaded.');

            // Extract dynamic Reflection Agent entries
            const reflection = payload.reflection || payload.summary || payload.discovery;
            setDiscoveryText(reflection || "I'm still reflecting on your journey.");

            // Normalize and parse Curiosity Agent responses (strings or structured maps)
            const rawQuestions = payload.questions || [];
            const normalizedQuestions: QuestionItem[] = rawQuestions.map((q, idx) => {
                if (typeof q === 'string') {
                    return { id: `q-${idx}`, text: q };
                }
                return q;
            });
            setQuestions(normalizedQuestions);

        } catch (error) {
            setStatus(error instanceof Error ? error.message : 'Unable to load graph.');
        } finally {
            setLoading(false);
        }
    }, [sessionId]);

    const handleMessageSent = useCallback(
        async (payload?: {
            graph?: any;
            discovery?: any;
            story_event?: any;
        }) => {
            if (!payload) {
                await loadGraph();
                return;
            }

            // Update Discovery
            if (payload.discovery) {
                setDiscovery(payload.discovery);
            }

            // Update Story Timeline
            if (payload.story_event) {
                console.log("Story Event:", payload.story_event);

                setStoryEvents((prev) => {
                    if (prev.some((e) => e.id === payload.story_event.id)) {
                        return prev;
                    }

                    return [payload.story_event, ...prev];
                });
            }

            // Refresh from backend (source of truth)
            await loadGraph();

            setStatus("🌿 Understanding Updated");
        },
        [loadGraph],
    );

    useEffect(() => {
        void loadGraph();
    }, [loadGraph]);

    const statusBannerElement = status ? (
        <div className="status-badge-pill">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <span>{status === 'Graph loaded.' ? '🌿 Understanding Updated' : status}</span>
        </div>
    ) : undefined;

    return (
        <Dashboard
            statusElement={statusBannerElement}
            graphViewElement={
                <GraphView
                    nodes={nodes}
                    edges={edges}
                    loading={loading}
                    onNodeSelect={(node) => setSelectedNodeId(node ? node.id : null)}
                />
            }
            chatPanelElement={
                <ChatPanel
                    sessionId={sessionId}
                    onMessageSent={handleMessageSent}
                />
            }
            chapterDetailsElement={
                <ChapterDetails
                    selectedNode={selectedNode}
                    nodes={nodes}
                    edges={edges}
                />
            }
            discoveryCardElement={
                <DiscoveryCard
                    text={discovery?.body || discoveryText}
                />
            }
            questionsCardElement={
                <QuestionsCard
                    questions={activeQuestions} // Injects derived curiosity prompts
                />
            }
            storyOfUnderstandingElement={
                <StoryOfUnderstanding
                    events={storyEvents}
                />
            }
        />
    );
}

export default App;