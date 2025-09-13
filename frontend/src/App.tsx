import React, { useState, useEffect } from 'react';
import { ThemeProvider } from './components/ThemeProvider';
import Header from './components/Header';
import Chat from './components/Chat';
import Canvas from './components/Canvas';
import './App.css';

function App() {
  const [isCanvasExpanded, setIsCanvasExpanded] = useState(false);
  const [simulationData, setSimulationData] = useState(null);

  const handleCanvasToggle = () => {
    setIsCanvasExpanded(!isCanvasExpanded);
  };

  const handleCanvasExpand = (data: any) => {
    setSimulationData(data);
    setIsCanvasExpanded(true);
  };

  const handleCanvasCollapse = () => {
    setIsCanvasExpanded(false);
  };

  return (
    <ThemeProvider>
      <div className="app">
        <Header />
        <main className="app-main">
          <div className={`app-content ${isCanvasExpanded ? 'canvas-expanded' : 'canvas-collapsed'}`}>
            <div className={`canvas-section ${isCanvasExpanded ? 'expanded' : 'collapsed'}`}>
              <Canvas 
                isExpanded={isCanvasExpanded}
                simulationData={simulationData}
                onToggle={handleCanvasToggle}
                onCollapse={handleCanvasCollapse}
              />
            </div>
            <div className="chat-section">
              <Chat 
                onCanvasExpand={handleCanvasExpand}
                isCanvasExpanded={isCanvasExpanded}
              />
            </div>
          </div>
        </main>
      </div>
    </ThemeProvider>
  );
}

export default App;