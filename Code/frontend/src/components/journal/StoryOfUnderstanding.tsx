import React, { useMemo } from 'react';

export interface JournalEventItem {
    id: string;
    timestamp: string;  // ISO Date string provided by the backend (e.g., '2026-07-04T12:00:00Z')
    title: string;
    summary: string;
    category?: string;
}

interface StoryOfUnderstandingProps {
    events: JournalEventItem[];
}

// Extensible registry mapping future backend timeline event types to elegant emojis
const EVENT_EMOJIS: Record<string, string> = {
    'concept_discovered': '🎯',
    'relationship_formed': '🔗',
    'reflection_updated': '🌿',
    'confidence_changed': '⚡',
    'curiosity_answered': '💬',
    'theme_strengthened': '🌱',
    'weekly_reflection': '📖',
};

const DEFAULT_EVENT_EMOJI = '📝';

const getEmojiForEvent = (category?: string): string => {
    if (!category) return DEFAULT_EVENT_EMOJI;
    return EVENT_EMOJIS[category.toLowerCase().trim()] ?? DEFAULT_EVENT_EMOJI;
};

// Helper: Group dates dynamically into relative calendar segments
const getRelativeGroup = (date: Date): 'Today' | 'Yesterday' | 'This Week' | 'Earlier' => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    const oneWeekAgo = new Date(today);
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
    
    const eventZeroTime = new Date(date.getFullYear(), date.getMonth(), date.getDate());

    if (eventZeroTime.getTime() === today.getTime()) return 'Today';
    if (eventZeroTime.getTime() === yesterday.getTime()) return 'Yesterday';
    if (eventZeroTime >= oneWeekAgo) return 'This Week';
    return 'Earlier';
};

export const StoryOfUnderstanding: React.FC<StoryOfUnderstandingProps> = ({ events = [] }) => {
    
    // Process backend events: parse dates, sort chronologically, and group relatively
    const groupedEvents = useMemo(() => {
        const groups: Record<'Today' | 'Yesterday' | 'This Week' | 'Earlier', JournalEventItem[]> = {
            Today: [],
            Yesterday: [],
            'This Week': [],
            Earlier: []
        };

        if (!events || events.length === 0) {
            return groups;
        }

        // Sort events chronologically descending (Newest first)
        const sortedEvents = [...events].sort((a, b) => {
            const dateA = new Date(a.timestamp).getTime();
            const dateB = new Date(b.timestamp).getTime();
            return dateB - dateA;
        });

        sortedEvents.forEach((event) => {
            const eventDate = new Date(event.timestamp);
            if (isNaN(eventDate.getTime())) return; // Gracefully filter invalid dates

            const period = getRelativeGroup(eventDate);
            groups[period].push(event);
        });

        return groups;
    }, [events]);

    const hasEvents = events && events.length > 0;

    return (
        <div className="journal-card" style={{ height: '100%', overflowY: 'auto' }}>
            <div className="journal-card-header">
                <span className="journal-card-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12 6 12 12 16 14" />
                    </svg>
                </span>
                <h3 className="journal-card-title">Story of Understanding</h3>
            </div>

            {!hasEvents ? (
                <p className="journal-card-content" style={{ fontStyle: 'italic', color: 'var(--muted-color)' }}>
                    "Our story is just beginning. As we speak, I will write the chapters of your journey here."
                </p>
            ) : (
                <div className="story-timeline-wrapper">
                    <div className="story-timeline-stem" />
                    
                    {Object.entries(groupedEvents).map(([period, periodEvents]) => {
                        if (periodEvents.length === 0) return null;
                        return (
                            <div key={period} className="story-timeline-period-group">
                                <h4 className="story-timeline-period-title">{period}</h4>
                                <div className="story-timeline-events-list">
                                    {periodEvents.map((event) => {
                                        const eventDate = new Date(event.timestamp);
                                        const dateStr = eventDate.toLocaleDateString(undefined, { 
                                            month: 'short', 
                                            day: 'numeric' 
                                        });
                                        const emoji = getEmojiForEvent(event.category);

                                        return (
                                            <div key={event.id} className="story-timeline-event-item">
                                                <div className="story-timeline-event-icon-circle">
                                                    {emoji}
                                                </div>
                                                <div className="story-timeline-event-details">
                                                    <h5
                                                        style={{
                                                            margin: 0,
                                                            fontWeight: 600,
                                                            fontSize: '0.95rem',
                                                        }}
                                                    >
                                                        {event.title}
                                                    </h5>

                                                    <p className="story-timeline-event-desc">
                                                        {event.summary}
                                                    </p>

                                                    <span className="story-timeline-event-date">
                                                        {dateStr}
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};
