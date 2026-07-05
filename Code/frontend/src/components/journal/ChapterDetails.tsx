import React from 'react';
import { type GraphViewNode } from '../GraphView';

interface ChapterDetailsProps {
    selectedNode: GraphViewNode | null;
}

interface MetadataFieldConfig {
    key: string;
    label: string;
    render?: (value: any) => React.ReactNode;
}

// Helper to extract readable text safely from dynamic objects, strings, or numbers
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
        // Prioritized list of keys commonly returning text/message structures
        const targetKeys = ['text', 'message', 'content', 'quote', 'value'];
        for (const key of targetKeys) {
            if (val[key] !== undefined && val[key] !== null) {
                return String(val[key]);
            }
        }
        // Fallback: look for the first string-type property inside the object
        const firstStringValue = Object.values(val).find((v) => typeof v === 'string');
        if (firstStringValue) {
            return String(firstStringValue);
        }
    }
    return '';
};

const METADATA_FIELDS_REGISTRY: MetadataFieldConfig[] = [
    {
        key: 'category',
        label: 'Classification',
        render: (val) => <span style={{ textTransform: 'capitalize' }}>{String(val)}</span>
    },
    {
        key: 'confidence',
        label: 'Confidence level',
        render: (val) => (
            <span style={{ fontWeight: 600, color: 'var(--primary-color)' }}>
                {typeof val === 'number' ? `${Math.round(val * 100)}%` : String(val)}
            </span>
        )
    },
    {
        key: 'relationships',
        label: 'Connected Themes',
        render: (val) => {
            const items = Array.isArray(val) 
                ? val 
                : String(val).split(',').map((item) => item.trim());
            return (
                <div className="details-meta-chip-group">
                    {items.map((item, idx) => (
                        <span key={idx} className="details-meta-chip">{item}</span>
                    ))}
                </div>
            );
        }
    },
    {
        key: 'evidence',
        label: 'Archival Evidence',
        render: (val) => {
            if (!val) return null;

            // Helper to clean up redundant enclosing quotes
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

            const renderQuoteBlock = (text: string, index?: number) => {
                const quoteText = cleanQuote(text);
                if (!quoteText) return null;
                return (
                    <blockquote key={index} className="details-meta-quote">
                        "{quoteText}"
                    </blockquote>
                );
            };

            // Render array elements cleanly as separate blocks
            if (Array.isArray(val)) {
                const renderedQuotes = val
                    .map((item) => extractText(item))
                    .filter((text) => text.trim().length > 0)
                    .map((text, idx) => renderQuoteBlock(text, idx));

                return renderedQuotes.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                        {renderedQuotes}
                    </div>
                ) : null;
            }

            // Render single value extract
            const extracted = extractText(val);
            return extracted ? renderQuoteBlock(extracted) : null;
        }
    },
    {
        key: 'lastUpdated',
        label: 'Recorded On'
    },
    {
        key: 'source',
        label: 'Origin Source'
    }
];

export const ChapterDetails: React.FC<ChapterDetailsProps> = ({ selectedNode }) => {
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
                <p className="journal-card-content">
                    "Select a concept to explore its story, relationships, and growth."
                </p>
            </div>
        );
    }

    const { label, description, ...extraData } = selectedNode.data || {};

    const activeMetadata = METADATA_FIELDS_REGISTRY.filter((field) => {
        const val = extraData[field.key];
        return val !== undefined && val !== null && val !== '';
    });

    return (
        <div className="journal-card" style={{ height: '100%', cursor: 'default' }}>
            <div className="journal-card-details-wrapper">
                <div className="details-title-row">
                    <span className="details-subtitle-type">
                        {String(extraData.type || extraData.category || 'Concept')}
                    </span>
                    <h2 className="details-main-title">{label || 'Unnamed Chapter'}</h2>
                </div>

                <p className="details-description-block">
                    {description || (
                        <span style={{ fontStyle: 'italic', color: 'var(--muted-color)' }}>
                            An active chapter in your map of understanding. Continue your conversations to deepen details and expand its relationships.
                        </span>
                    )}
                </p>

                {activeMetadata.length > 0 && (
                    <div className="details-meta-grid">
                        {activeMetadata.map((field) => {
                            const value = extraData[field.key];
                            return (
                                <div key={field.key} className="details-meta-item">
                                    <span className="details-meta-label">{field.label}</span>
                                    <div className="details-meta-value">
                                        {field.render ? field.render(value) : String(value)}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};