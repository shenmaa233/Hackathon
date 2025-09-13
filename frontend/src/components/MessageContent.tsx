import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import ImagePlaceholder from './ImagePlaceholder';
import './MessageContent.css';

interface MessageContentProps {
  content: string;
  isStreaming?: boolean;
}

// 检测图片URL的正则表达式
const IMAGE_URL_REGEX = /(https?:\/\/[^\s]+\.(jpg|jpeg|png|gif|webp|svg)(\?[^\s]*)?)/gi;
const MARKDOWN_IMAGE_REGEX = /!\[([^\]]*)\]\(([^)]+)\)/g;
// 检测可能的图片链接开头（用于流式传输时的预处理）
const POTENTIAL_IMAGE_START = /(https?:\/\/[^\s]*)/gi;
// 常见的图片服务域名模式
const IMAGE_DOMAIN_PATTERNS = [
  'imgur', 'image', 'pic', 'photo', 'cdn', 'media', 'static', 'assets',
  'upload', 'storage', 'blob', 'cloudinary', 'amazonaws', 'googleusercontent'
];

// 辅助函数：检测并隐藏流式传输中的图片链接
const hideStreamingImageLinks = (text: string): string => {
  let processed = text;
  
  // 1. 隐藏不完整的Markdown图片语法 ![...
  processed = processed.replace(/!\[[^\]]*$/, '[图片生成中...]');
  processed = processed.replace(/!\[[^\]]*\]$/, '[图片生成中...]');
  processed = processed.replace(/!\[[^\]]*\]\([^)]*$/, '[图片生成中...]');
  
  // 2. 隐藏可能的不完整图片URL
  processed = processed.replace(/(https?:\/\/[^\s]{20,})/g, (match) => {
    // 如果是完整的图片链接，保持不变
    if (IMAGE_URL_REGEX.test(match)) {
      return match;
    }
    
    // 如果包含图片服务关键词，隐藏链接
    const containsImageKeyword = IMAGE_DOMAIN_PATTERNS.some(pattern => 
      match.toLowerCase().includes(pattern)
    );
    
    if (containsImageKeyword) {
      return '[图片链接生成中...]';
    }
    
    return match;
  });
  
  return processed;
};

const MessageContent: React.FC<MessageContentProps> = ({ content, isStreaming }) => {
  const [processedContent, setProcessedContent] = useState(content);
  const [detectedImages, setDetectedImages] = useState<string[]>([]);
  const [loadingImages, setLoadingImages] = useState<Set<string>>(new Set());

  // 处理内容，检测和处理图片链接
  useEffect(() => {
    let processed = content;
    const imageUrls: string[] = [];
    const newLoadingImages = new Set<string>();

    if (isStreaming) {
      // 流式传输时：隐藏不完整的内容
      processed = hideStreamingImageLinks(content);
      
      // 检测完整的图片链接并处理
      const completeImageMatches = content.match(IMAGE_URL_REGEX);
      if (completeImageMatches) {
        completeImageMatches.forEach(url => {
          // 只处理不是markdown格式的直接链接
          if (!content.includes(`![`) || !content.includes(`](${url})`)) {
            imageUrls.push(url);
            processed = processed.replace(url, `[图片生成中...]`);
            newLoadingImages.add(url);
          }
        });
      }
      
      // 如果检测到图片生成相关的隐藏内容，显示加载状态
      if (processed.includes('[图片生成中...]') || processed.includes('[图片链接生成中...]')) {
        newLoadingImages.add('generating');
      }
    } else {
      // 非流式传输时：转换所有图片链接为markdown格式
      const directImageMatches = content.match(IMAGE_URL_REGEX);
      if (directImageMatches) {
        directImageMatches.forEach(url => {
          // 如果不是已经是markdown格式的图片
          if (!content.match(new RegExp(`!\\[[^\\]]*\\]\\(${url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\)`))) {
            imageUrls.push(url);
            processed = processed.replace(url, `![生成的图片](${url})`);
          }
        });
      }
    }

    setDetectedImages(imageUrls);
    setLoadingImages(newLoadingImages);
    setProcessedContent(processed);
  }, [content, isStreaming]);

  // 当流式传输结束时，转换图片链接
  useEffect(() => {
    if (!isStreaming && detectedImages.length > 0) {
      let processed = content;
      detectedImages.forEach(url => {
        // 将隐藏的链接转换为markdown图片
        processed = processed.replace(`[图片生成中...]`, `![生成的图片](${url})`);
        processed = processed.replace(url, `![生成的图片](${url})`);
      });
      setProcessedContent(processed);
      setLoadingImages(new Set()); // 清除加载状态
    }
  }, [isStreaming, detectedImages, content]);
  // 自定义组件渲染
  const components = {
    // 自定义图片渲染
    img: ({ src, alt, ...props }: any) => {
      const [imageLoaded, setImageLoaded] = useState(false);
      const [imageError, setImageError] = useState(false);
      
      return (
        <div className="message-image-container">
          {!imageLoaded && !imageError && (
            <ImagePlaceholder text="加载图片中" />
          )}
          <img 
            src={src} 
            alt={alt || '生成的图片'} 
            className={`message-image ${imageLoaded ? 'loaded' : 'loading'}`}
            loading="lazy"
            onLoad={() => setImageLoaded(true)}
            onError={() => {
              setImageError(true);
              setImageLoaded(false);
            }}
            style={{ display: imageLoaded ? 'block' : 'none' }}
            {...props}
          />
          {imageError && (
            <div className="image-error">
              图片加载失败: {alt || '未知图片'}
            </div>
          )}
        </div>
      );
    },
    
    // 自定义链接渲染
    a: ({ href, children, ...props }: any) => (
      <a 
        href={href} 
        target="_blank" 
        rel="noopener noreferrer" 
        className="message-link"
        {...props}
      >
        {children}
      </a>
    ),
    
    // 自定义代码块渲染
    code: ({ node, inline, className, children, ...props }: any) => {
      const match = /language-(\w+)/.exec(className || '');
      return !inline && match ? (
        <div className="code-block-container">
          <div className="code-block-header">
            <span className="code-language">{match[1]}</span>
            <button 
              className="code-copy-btn"
              onClick={() => {
                navigator.clipboard.writeText(String(children).replace(/\n$/, ''));
              }}
            >
              复制
            </button>
          </div>
          <pre className={className} {...props}>
            <code>{children}</code>
          </pre>
        </div>
      ) : (
        <code className="inline-code" {...props}>
          {children}
        </code>
      );
    },
    
    // 自定义表格渲染
    table: ({ children, ...props }: any) => (
      <div className="table-container">
        <table className="message-table" {...props}>
          {children}
        </table>
      </div>
    ),
    
    // 自定义引用块渲染
    blockquote: ({ children, ...props }: any) => (
      <blockquote className="message-blockquote" {...props}>
        {children}
      </blockquote>
    ),
  };

  return (
    <div className={`message-content-wrapper ${isStreaming ? 'streaming' : ''}`}>
      {/* 显示图片加载占位符 */}
      {loadingImages.size > 0 && (
        <ImagePlaceholder text="正在生成图片" />
      )}
      
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={components}
        className="message-markdown"
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
};

export default MessageContent;
