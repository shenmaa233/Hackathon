import React from 'react';
import { ThemeProvider } from './components/ThemeProvider';
import Header from './components/Header';
import Chat from './components/Chat';
import Canvas from './components/Canvas';
import './App.css';

function App() {
  return (
    <ThemeProvider>
      <div className="app">
        <Header />
        <main className="app-main">
          <div className="app-content">
            <div className="canvas-section">
              <Canvas />
            </div>
            <div className="chat-section">
              <Chat />
            </div>
          </div>
        </main>
      </div>
    </ThemeProvider>
  );
}

export default App;