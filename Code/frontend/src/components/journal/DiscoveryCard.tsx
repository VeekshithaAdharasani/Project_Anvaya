import React from 'react';

interface DiscoveryCardProps {
    text: string;
}

export const DiscoveryCard: React.FC<DiscoveryCardProps> = ({ text }) => {
  const isDefaultReflecting = 
    !text || 
    text.trim() === "" || 
    text.toLowerCase().includes("reflecting on your journey") ||
    text.toLowerCase().includes("reflecting on our journey");

  const displayText = isDefaultReflecting
    ? "I'm still reflecting on today's conversations. As we talk more, new patterns will gradually emerge."
    : text;

  return (
    <div className="journal-card">
      <div className="journal-card-header">
        <span className="journal-card-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z" />
            <line x1="16" y1="8" x2="2" y2="22" />
            <line x1="17.5" y1="15" x2="9" y2="15" />
          </svg>
        </span>
        <h3 className="journal-card-title">Today's Discovery</h3>
      </div>
      <p className={`journal-card-content discovery-card-text ${isPlaceholderText(displayText) ? 'poetic-placeholder' : ''}`}>
        {displayText}
      </p>
    </div>
  );
};

// Helper to check if text matches the placeholder to apply soft styling
const isPlaceholderText = (val: string): boolean => {
  return val.includes("reflecting on today's conversations");
};