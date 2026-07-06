import React, { useMemo } from 'react';

export interface QuestionItem {
    id?: string;
    text: string;
    category?: string;
    conceptId?: string;
    isPrimary?: boolean;
    isAnswered?: boolean;
}

interface QuestionsCardProps {
    questions: QuestionItem[];
}

export const QuestionsCard: React.FC<QuestionsCardProps> = ({ questions }) => {
    // 1. Dynamic Deduplication and Pruning of Answered Prompts
    const activeQuestions = useMemo(() => {
        const seen = new Set<string>();
        return questions
            .filter((q) => q.isAnswered !== true) // Filter out answered questions
            .filter((q) => {
                const identifier = q.id || q.text;
                if (seen.has(identifier)) return false;
                seen.add(identifier);
                return true;
            });
    }, [questions]);

    // 2. Separate Primary Priority vs. Secondary Lists
    const { primary, secondary } = useMemo(() => {
        if (activeQuestions.length === 0) {
            return { primary: null, secondary: [] };
        }
        
        // Find explicitly prioritized primary, default to first item otherwise
        const primaryIndex = activeQuestions.findIndex((q) => q.isPrimary === true);
        const activePrimaryIndex = primaryIndex !== -1 ? primaryIndex : 0;
        
        const primaryQuery = activeQuestions[activePrimaryIndex];
        const secondaryQueries = activeQuestions.filter((_, idx) => idx !== activePrimaryIndex);

        return {
            primary: primaryQuery,
            secondary: secondaryQueries,
        };
    }, [activeQuestions]);

    // 3. Poetic placeholder if Curiosity Agent returns empty response
    if (!primary) {
        return (
            <div className="journal-card" style={{ height: '100%', cursor: 'default' }}>
                <div className="journal-card-header">
                    <span className="journal-card-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707.707M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />
                        </svg>
                    </span>
                    <h3 className="journal-card-title">Questions Worth Exploring</h3>
                </div>
                <p className="journal-card-content poetic-placeholder" style={{ fontStyle: 'italic', color: 'var(--muted-color)', opacity: 0.8 }}>
                    "I am quietly listening. As we converse more, new paths of curiosity will open up."
                </p>
            </div>
        );
    }

    return (
        <div className="journal-card" style={{ height: '100%', cursor: 'default' }}>
            <div className="journal-card-header">
                <span className="journal-card-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707.707M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />
                    </svg>
                </span>
                <h3 className="journal-card-title">Questions Worth Exploring</h3>
            </div>

            {/* key forces transition resets when question payload indices change */}
            <div className="questions-animate-fade" key={primary.text}>
                <p className="questions-primary-text">
                    {primary.text}
                </p>

                {/* 4. Display secondary questions only if available */}
                {secondary.length > 0 && (
                    <div className="questions-secondary-section">
                        <h4 className="questions-secondary-title">Other areas to explore</h4>
                        <ul className="questions-secondary-list">
                            {secondary.map((sec, idx) => (
                                <li key={sec.id || idx} className="questions-secondary-item">
                                    <span className="questions-bullet">✦</span>
                                    <span>{sec.text}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    );
};