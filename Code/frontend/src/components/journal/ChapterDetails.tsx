import React from 'react';
import {
    type GraphViewNode,
    type GraphViewEdge,
} from '../GraphView';

interface ChapterDetailsProps {
    selectedNode: GraphViewNode | null;
    nodes: GraphViewNode[];
    edges: GraphViewEdge[];
}

// Extensible registry mapping categories to storytelling emojis
const CATEGORY_EMOJIS: Record<string, string> = {
    goal: '🎯',
    goals: '🎯',
    skill: '🧠',
    skills: '🧠',
    learning: '🧠',
    project: '🚀',
    projects: '🚀',
    interest: '💖',
    interests: '💖',
    value: '💎',
    values: '💎',
    trait: '🛡️',
    traits: '🛡️',
    dream: '✨',
    dreams: '✨',
    motivation: '🔥',
    motivations: '🔥',
};

const DEFAULT_EMOJI = '📝';

const getEmojiForCategory = (category: string): string => {
    const key = category.toLowerCase().trim();
    return CATEGORY_EMOJIS[key] ?? DEFAULT_EMOJI;
};

// Helper to extract readable text safely from dynamic evidence objects or arrays
const extractText = (val: any): string => {
    if (val === undefined || val === null) {
        return '';
    }
    if (typeof val === 'string') {
        return val;
    }
    if (typeof val === 'number') {
        return String(val);
    }
    if (typeof val === 'object') {
        const targetKeys = ['text', 'message', 'content', 'quote', 'value'];
        for (const key of targetKeys) {
            if (val[key] !== undefined && val[key] !== null) {
                return String(val[key]);
            }
        }
        const firstStringValue = Object.values(val).find((v) => typeof v === 'string');
        if (firstStringValue) {
            return String(firstStringValue);
        }
    }
    return '';
};

export const ChapterDetails: React.FC<ChapterDetailsProps> = ({ selectedNode, nodes, edges }) => {
    if (!selectedNode) {
        return (
            <div className="journal-card">
                <div className="journal-card-header">
                    <span className="journal-card-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                        </svg>
                    </span>
                    <h3 className="journal-card-title">Chapter Details</h3>
                </div>
                <p className="journal-card-content" style={{ fontStyle: 'italic', color: 'var(--muted-color)' }}>
                    "Select a concept to explore its story, relationships, and growth."
                </p>
            </div>
        );
    }

    const { label, description, ...extraData } = selectedNode.data || {};
    const category = String(extraData.type || extraData.category || 'Concept');
    const conceptEmoji = getEmojiForCategory(category);

    // Filter connected nodes
    const connectedRelationships = edges.filter(
        (edge) => edge.source === selectedNode.id || edge.target === selectedNode.id
    );
    const connectedConcepts = connectedRelationships.map((edge) => {
        const otherNodeId = edge.source === selectedNode.id ? edge.target : edge.source;
        return nodes.find((n) => n.id === otherNodeId);
    }).filter((n): n is GraphViewNode => n !== undefined);

    const journalSubtitle = `${category.charAt(0).toUpperCase() + category.slice(1).toLowerCase()}`;

    // Clean archival quotes helper
    const cleanQuote = (str: string) => {
        const trimmed = str.trim();
        if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
            return trimmed.substring(1, trimmed.length - 1);
        }
        if (trimmed.startsWith("'") && trimmed.endsWith("'")) {
            return trimmed.substring(1, trimmed.length - 1);
        }
        return trimmed;
    };

    const rawEvidence = extraData.evidence;
    const hasEvidence = rawEvidence !== undefined && rawEvidence !== null && rawEvidence !== '';

    // Render timeline dates
    const formatDate = (val: any) => {
        if (!val) return null;
        try {
            return new Date(val).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
            });
        } catch {
            return String(val);
        }
    };

    const firstDiscovered = formatDate(extraData.created_at);
    const lastRevisited = formatDate(extraData.updated_at || extraData.created_at);

    return (
        <div className="journal-card" style={{ height: '100%', cursor: 'default' }}>
            <div className="journal-card-details-wrapper">
                
                {/* Header Block */}
                <div className="details-header-divider">
                    <div className="details-header-title-container">
                        <span className="details-header-emoji">{conceptEmoji}</span>
                        <h2 className="details-main-title">
                            {label || 'Unnamed Chapter'}
                        </h2>
                    </div>
                    <span className="details-header-subtitle">
                        {journalSubtitle}
                    </span>
                </div>

                {/* Main Concept Narrative Description */}
                <div>
                    <p className="details-paragraph">
                        {description || "This chapter has no description yet. Continue your conversations to deepen its story as your understanding map evolves."}
                    </p>
                </div>

                {/* Narrative Evidence Block (Why I believe this) */}
                {hasEvidence && (
                    <div className="details-section-container">
                        <h4 className="details-section-title">
                            Why I believe this
                        </h4>
                        <p className="details-section-subtitle">
                            {extraData.validation_status?.toString().toLowerCase() === 'inferred'
                                ? `I've noticed this theme emerging organically through our conversations.`
                                : `You shared this directly during our dialogue, emphasizing its importance in your life.`}
                        </p>
                        
                        <div className="details-section-quote-group">
                            {Array.isArray(rawEvidence) ? (
                                rawEvidence.map((item, idx) => {
                                    const text = cleanQuote(extractText(item));
                                    if (!text) return null;
                                    return (
                                        <blockquote key={idx} className="details-meta-quote">
                                            "{text}"
                                        </blockquote>
                                    );
                                })
                            ) : (
                                <blockquote className="details-meta-quote">
                                    "{cleanQuote(extractText(rawEvidence))}"
                                </blockquote>
                            )}
                        </div>
                    </div>
                )}

                {/* Reflection Narrative Block */}
                <div className="details-section-container">
                    <h4 className="details-section-title">
                        Reflection
                    </h4>
                    <p className="details-reflection-text">
                        {extraData.reflection || "Reflection will grow as I learn more about this part of your story."}
                    </p>
                </div>

                {/* Connected Concepts Section */}
                {connectedConcepts.length > 0 && (
                    <div className="details-section-container">
                        <h4 className="details-section-title">
                            Connected Chapters
                        </h4>
                        <div className="details-connections-group">
                            {connectedConcepts.map((node, index) => {
                                const connCat = String(node.data?.category || node.data?.type || '');
                                const connLabel = String(node.data?.label || 'Concept');
                                const connEmoji = getEmojiForCategory(connCat);
                                return (
                                    <span key={index} className="details-connection-chip">
                                        <span>{connEmoji}</span>
                                        <span>{connLabel}</span>
                                    </span>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Historical Timeline (Journey) */}
                {(firstDiscovered || lastRevisited) && (
                    <div className="details-timeline-container">
                        {firstDiscovered && (
                            <div className="details-timeline-item">
                                <span className="details-timeline-label">First discovered</span>
                                <span>{firstDiscovered}</span>
                            </div>
                        )}
                        {lastRevisited && (
                            <div className="details-timeline-item right-align">
                                <span className="details-timeline-label">Last revisited</span>
                                <span>{lastRevisited}</span>
                            </div>
                        )}
                    </div>
                )}

            </div>
        </div>
    );
};