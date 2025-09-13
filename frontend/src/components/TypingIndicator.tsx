import React from 'react';
import './TypingIndicator.css';

interface TypingIndicatorProps {
  text?: string;
}

const TypingIndicator: React.FC<TypingIndicatorProps> = ({ text = "AI正在思考中" }) => {
  return (
    <div className="typing-indicator-modern">
      <div className="typing-dots">
        <div className="typing-dot"></div>
        <div className="typing-dot"></div>
        <div className="typing-dot"></div>
      </div>
      <span className="typing-text">{text}...</span>
    </div>
  );
};

export default TypingIndicator;
