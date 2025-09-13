import React, { useRef, useState, useEffect } from 'react';
import { Canvas as ThreeCanvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, Environment, Line } from '@react-three/drei';
import * as THREE from 'three';
import PICVisualization from './PICVisualization';
import './Canvas.css';

interface CanvasProps {
  isExpanded: boolean;
  simulationData: any;
  onToggle: () => void;
  onCollapse: () => void;
}

// 旋转的立方体组件
function RotatingCube() {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const [clicked, setClicked] = useState(false);

  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.x += delta * 0.5;
      meshRef.current.rotation.y += delta * 0.3;
      meshRef.current.scale.setScalar(clicked ? 1.2 : hovered ? 1.1 : 1);
    }
  });

  return (
    <mesh
      ref={meshRef}
      onClick={() => setClicked(!clicked)}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
    >
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial 
        color={clicked ? '#10a37f' : hovered ? '#20b2aa' : '#4fd1c7'} 
        metalness={0.3}
        roughness={0.2}
      />
    </mesh>
  );
}

// 浮动的球体
function FloatingSphere({ position }: { position: [number, number, number] }) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 2) * 0.3;
    }
  });

  return (
    <mesh ref={meshRef} position={position}>
      <sphereGeometry args={[0.3, 32, 32]} />
      <meshStandardMaterial 
        color="#ff6b6b" 
        metalness={0.5}
        roughness={0.1}
        transparent
        opacity={0.8}
      />
    </mesh>
  );
}

const Canvas: React.FC<CanvasProps> = ({ isExpanded, simulationData, onToggle, onCollapse }) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showPICVisualization, setShowPICVisualization] = useState(false);

  useEffect(() => {
    if (simulationData) {
      setShowPICVisualization(true);
    }
  }, [simulationData]);

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const handleClose = () => {
    setShowPICVisualization(false);
    onCollapse();
  };

  return (
    <div className={`canvas-container ${isFullscreen ? 'fullscreen' : ''}`}>
      <div className="canvas-header">
        <div className="canvas-title">
          <h3>{showPICVisualization ? 'PIC等离子体模拟' : '3D 可视化画布'}</h3>
          <p>{showPICVisualization ? '粒子-单元等离子体物理模拟' : '交互式3D展示区域'}</p>
        </div>
        <div className="canvas-controls">
          {isExpanded && (
            <button
              className="control-button"
              onClick={handleClose}
              title="关闭画布"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path
                  d="M18 6L6 18M6 6l12 12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          )}
          <button
            className="control-button"
            onClick={toggleFullscreen}
            title={isFullscreen ? '退出全屏' : '全屏显示'}
          >
            {isFullscreen ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path
                  d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path
                  d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        </div>
      </div>

      <div className="canvas-content">
        <ThreeCanvas
          camera={{ position: showPICVisualization ? [0, 0, 15] : [3, 3, 3], fov: 75 }}
          style={{ background: 'transparent' }}
        >
          {/* 环境光和点光源 */}
          <ambientLight intensity={0.4} />
          <pointLight position={[10, 10, 10]} intensity={1} />
          <pointLight position={[-10, -10, -10]} intensity={0.5} color="#4fd1c7" />

          {showPICVisualization ? (
            /* PIC模拟可视化 */
            <PICVisualization simulationData={simulationData} />
          ) : (
            /* 默认的3D场景 */
            <>
              {/* 主要的旋转立方体 */}
              <RotatingCube />

              {/* 浮动的球体们 */}
              <FloatingSphere position={[-2, 1, 0]} />
              <FloatingSphere position={[2, -1, 0]} />
              <FloatingSphere position={[0, 2, -2]} />

              {/* 网格地面 */}
              <Grid
                args={[10, 10]}
                position={[0, -2, 0]}
                cellSize={0.5}
                cellThickness={0.5}
                cellColor="#6b7280"
                sectionSize={2}
                sectionThickness={1}
                sectionColor="#4b5563"
                fadeDistance={25}
                fadeStrength={1}
                infiniteGrid
              />

              {/* 环境贴图 */}
              <Environment preset="city" />
            </>
          )}

          {/* 轨道控制器 */}
          <OrbitControls
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
            minDistance={showPICVisualization ? 5 : 2}
            maxDistance={showPICVisualization ? 50 : 20}
          />
        </ThreeCanvas>

        <div className="canvas-info">
          <div className="info-item">
            <span className="info-label">操作提示:</span>
            <span className="info-value">
              {showPICVisualization 
                ? '鼠标拖拽旋转 • 滚轮缩放 • 蓝色/红色点为粒子 • 橙色线为电场'
                : '鼠标拖拽旋转 • 滚轮缩放 • 点击立方体'
              }
            </span>
          </div>
          {showPICVisualization && simulationData?.data && (
            <div className="info-item">
              <span className="info-label">模拟信息:</span>
              <span className="info-value">
                类型: {simulationData.data.simulation_params?.simulation_type || 'unknown'} • 
                帧数: {simulationData.data.frames?.length || 0}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Canvas;