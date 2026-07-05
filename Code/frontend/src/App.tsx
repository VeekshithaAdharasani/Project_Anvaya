import { useCallback, useEffect, useMemo, useState } from 'react';
import GraphView, { type GraphViewEdge, type GraphViewNode } from './components/GraphView';
import ChatPanel from './components/ChatPanel';
import { Dashboard } from './components/layouts/Dashboard';
import { ChapterDetails } from './components/journal/ChapterDetails';
import { DiscoveryCard } from './components/journal/DiscoveryCard';
import { QuestionsCard, type QuestionItem } from './components/journal/QuestionsCard';
import { fetchGraph, type GraphPayload } from './services/graphService';

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
            const payload = (await fetchGraph(sessionId)) as ExtendedGraphPayload;
            setNodes(
                payload.nodes.map((node, index) => ({
                    id: node.id,
                    type: 'default',
                    position: { x: (index % 4) * 180, y: Math.floor(index / 4) * 120 },
                    data: { label: node.label, ...node.data },
                })),
            );
            setEdges(
                payload.edges.map((edge) => ({
                    id: edge.id,
                    source: edge.source,
                    target: edge.target,
                    type: 'default',
                    data: edge.data,
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
                    onMessageSent={loadGraph} 
                />
            }
            chapterDetailsElement={
                <ChapterDetails 
                    selectedNode={selectedNode} 
                />
            }
            discoveryCardElement={
                <DiscoveryCard 
                    text={discoveryText} 
                />
            }
            questionsCardElement={
                <QuestionsCard 
                    questions={activeQuestions} // Injects derived curiosity prompts
                />
            }
        />
    );
}

export default App;