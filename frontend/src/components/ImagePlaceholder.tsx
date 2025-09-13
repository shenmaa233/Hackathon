import React from 'react';
import './ImagePlaceholder.css';

interface ImagePlaceholderProps {
  text?: string;
}

const ImagePlaceholder: React.FC<ImagePlaceholderProps> = ({ text = "正在生成图片" }) => {
  return (
    <div className="image-placeholder">
      <div className="image-placeholder-content">
        <div className="image-placeholder-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" stroke="currentColor" strokeWidth="2"/>
            <circle cx="8.5" cy="8.5" r="1.5" stroke="currentColor" strokeWidth="2"/>
            <polyline points="21,15 16,10 5,21" stroke="currentColor" strokeWidth="2"/>
          </svg>
        </div>
        <div className="image-placeholder-text">{text}...</div>
        <div className="image-placeholder-progress">
          <div className="progress-bar"></div>
        </div>
      </div>
    </div>
  );
};

export default ImagePlaceholder;
