import React from 'react';

export const Header: React.FC = () => {
  return (
    <header className="journal-header">
      <span className="journal-header-badge">The Living Journal</span>
      <h1 className="journal-logo">ANVAYA</h1>
      <p className="journal-subtitle">From Memory to Understanding</p>
    </header>
  );
};