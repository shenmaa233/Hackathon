import React, { useState, useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import './Chat.css';

interface Message {
  id: string;
  content: string;
  type: 'user' | 'assistant';
  timestamp: Date;
  isStreaming?: boolean;
}

// 1. 在组件外部创建 socket 实例，防止在 React 严格模式下重复创建和销毁
// --- 核心修改在这里 ---
const backendUrl = 'http://localhost:8080'; // 确认后端地址

// 移除 transports: ['websocket']
const socket: Socket = io(backendUrl, {
  autoConnect: false, 
});

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(socket.connected);
  const [isGenerating, setIsGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // 只有在 socket 未连接时才手动连接
    if (!socket.connected) {
      socket.connect();
    }

    const handleConnect = () => {
      setIsConnected(true);
      console.log('Connected to server');
    };

    const handleDisconnect = () => {
      setIsConnected(false);
      setIsGenerating(false);
      console.log('Disconnected from server');
    };

    const handleGenerationStarted = () => {
      setIsLoading(false);
      setIsGenerating(true);
      
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        content: '',
        type: 'assistant',
        timestamp: new Date(),
        isStreaming: true,
      };
      setMessages(prev => [...prev, assistantMessage]);
    };

    const handleResponseChunk = (data: { full_response: string }) => {
      setMessages(prev => 
        prev.map(msg => 
          (msg.isStreaming && msg.type === 'assistant')
            ? { ...msg, content: data.full_response } 
            : msg
        )
      );
    };

    const handleGenerationCompleted = () => {
      setIsGenerating(false);
      setMessages(prev => 
        prev.map(msg => 
          (msg.isStreaming && msg.type === 'assistant') 
            ? { ...msg, isStreaming: false } 
            : msg
        )
      );
    };

    const handleGenerationStopped = () => {
      setIsGenerating(false);
      setMessages(prev =>
        prev.map(msg => {
          if (msg.isStreaming && msg.type === 'assistant') {
            return {
              ...msg,
              isStreaming: false,
              content: msg.content.trim() ? msg.content : '[生成已停止]',
            };
          }
          return msg;
        })
      );
    };

    const handleError = (data: { message: string }) => {
      console.error('Socket error:', data.message);
      setIsLoading(false);
      setIsGenerating(false);
      
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        content: `错误: ${data.message}`,
        type: 'assistant', // 显示为助手消息
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    };
    
    // 新增：监听后端历史记录清除事件，确保前后端同步
    const handleHistoryCleared = () => {
        setMessages([]);
        console.log('History cleared by server confirmation.');
    };

    // 绑定事件
    socket.on('connect', handleConnect);
    socket.on('disconnect', handleDisconnect);
    socket.on('generation_started', handleGenerationStarted);
    socket.on('response_chunk', handleResponseChunk);
    socket.on('generation_completed', handleGenerationCompleted);
    socket.on('generation_stopped', handleGenerationStopped);
    socket.on('error', handleError);
    socket.on('history_cleared', handleHistoryCleared);

    // 清理函数：只移除事件监听器，不主动断开连接
    return () => {
      socket.off('connect', handleConnect);
      socket.off('disconnect', handleDisconnect);
      socket.off('generation_started', handleGenerationStarted);
      socket.off('response_chunk', handleResponseChunk);
      socket.off('generation_completed', handleGenerationCompleted);
      socket.off('generation_stopped', handleGenerationStopped);
      socket.off('error', handleError);
      socket.off('history_cleared', handleHistoryCleared);
    };
  }, []); // 空依赖数组确保这个 effect 只运行一次

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = () => {
    if (!input.trim() || isLoading || isGenerating) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      content: input.trim(),
      type: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    socket.emit('message', { message: input.trim() });
    setInput('');
    setIsLoading(true);
    
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };
  
  const stopGeneration = () => {
    if (isGenerating) {
      socket.emit('stop_generation', {});
    }
  };

  const clearHistory = () => {
    if (!isGenerating) {
      // 2. 让后端来确认清除，而不是前端直接操作
      socket.emit('clear_history', {});
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    // ... JSX 部分与您原来的一样，无需修改 ...
    <div className="chat-container">
        {/* ... Header ... */}
        <div className="chat-header">
            <div className="connection-status">
                <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></div>
                <span className="status-text">{isConnected ? '已连接' : '连接中...'}</span>
            </div>
            <div className="chat-actions">
                <button
                    className="clear-button"
                    onClick={clearHistory}
                    disabled={isGenerating || messages.length === 0}
                    title="清除对话历史"
                >
                    {/* SVG Icon */}
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </button>
            </div>
        </div>
        {/* ... Messages Container ... */}
        <div className="messages-container">
            {messages.length === 0 ? (
                <div className="empty-state">
                    {/* ... Empty State SVG and text ... */}
                </div>
            ) : (
                <>
                    {messages.map((message) => (
                        <div key={message.id} className={`message ${message.type} fade-in`}>
                            {/* ... Message structure ... */}
                            <div className="message-content">
                                <div className={`message-text ${message.isStreaming ? 'streaming' : ''}`}>
                                    {message.content}
                                    {message.isStreaming && <span className="cursor-blink">▋</span>}
                                </div>
                                <div className="message-time">{formatTime(message.timestamp)}</div>
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="message assistant fade-in">
                            {/* ... Typing Indicator ... */}
                        </div>
                    )}
                </>
            )}
            <div ref={messagesEndRef} />
        </div>
        {/* ... Input Form ... */}
        <form onSubmit={handleSubmit} className="input-form">
            <div className="input-container">
                <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    placeholder={isGenerating ? "AI正在回复中..." : "输入消息..."}
                    className="message-input"
                    rows={1}
                    disabled={!isConnected || isLoading || isGenerating}
                />
                {isGenerating ? (
                    <button type="button" className="stop-button" onClick={stopGeneration} title="停止生成">
                        {/* Stop SVG Icon */}
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" /></svg>
                    </button>
                ) : (
                    <button type="submit" className={`send-button ${input.trim() && isConnected && !isLoading ? 'active' : ''}`} disabled={!input.trim() || !isConnected || isLoading} title="发送消息">
                        {/* Send SVG Icon */}
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    </button>
                )}
            </div>
        </form>
    </div>
  );
};

export default Chat;