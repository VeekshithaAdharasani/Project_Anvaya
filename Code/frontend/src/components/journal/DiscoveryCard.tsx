interface DiscoveryCardProps {
    text: string;
}

export const DiscoveryCard: React.FC<DiscoveryCardProps> = ({ text }) => {
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
      <p className="journal-card-content">
        {text}
      </p>
    </div>
  );
};