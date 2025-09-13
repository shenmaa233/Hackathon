import React, { useRef, useState, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import { Line } from '@react-three/drei';
import * as THREE from 'three';

interface PICVisualizationProps {
  simulationData: any;
}

// 粒子点云组件
function ParticleCloud({ positions, velocities, color }: { positions: number[], velocities: number[], color: string }) {
  const pointsRef = useRef<THREE.Points>(null);
  const [geometry, setGeometry] = useState<THREE.BufferGeometry>();

  useEffect(() => {
    if (positions && positions.length > 0) {
      const geo = new THREE.BufferGeometry();
      const posArray = new Float32Array(positions.length * 3);
      
      // 将1D位置和速度转换为3D点云
      for (let i = 0; i < positions.length; i++) {
        posArray[i * 3] = (positions[i] / 64) * 20 - 10; // x: 位置映射到 -10 到 10
        posArray[i * 3 + 1] = (velocities[i] / 15) * 10; // y: 速度映射到 -10 到 10
        posArray[i * 3 + 2] = 0; // z: 固定为0
      }
      
      geo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
      setGeometry(geo);
    }
  }, [positions, velocities]);

  if (!geometry) return null;

  return (
    <points ref={pointsRef} geometry={geometry}>
      <pointsMaterial 
        color={color} 
        size={0.1} 
        transparent
        opacity={0.6}
        vertexColors={false}
      />
    </points>
  );
}

// 电场可视化组件
function ElectricFieldVisualization({ fieldData }: { fieldData: number[] }) {
  const linePoints = React.useMemo(() => {
    if (!fieldData || fieldData.length === 0) return [];
    
    const points: [number, number, number][] = [];
    const scale = 20 / fieldData.length; // 映射到 -10 到 10 的范围
    
    for (let i = 0; i < fieldData.length; i++) {
      const x = (i / fieldData.length) * 20 - 10;
      const y = fieldData[i] * 2; // 缩放电场值
      points.push([x, y, 1]);
    }
    
    return points;
  }, [fieldData]);

  if (linePoints.length === 0) return null;

  return (
    <Line
      points={linePoints}
      color="orange"
      lineWidth={2}
      transparent
      opacity={0.8}
    />
  );
}

// 电势可视化组件
function PotentialVisualization({ potentialData }: { potentialData: number[] }) {
  const linePoints = React.useMemo(() => {
    if (!potentialData || potentialData.length === 0) return [];
    
    const points: [number, number, number][] = [];
    
    for (let i = 0; i < potentialData.length; i++) {
      const x = (i / potentialData.length) * 20 - 10;
      const y = potentialData[i] * 0.5; // 缩放电势值
      points.push([x, y, -1]);
    }
    
    return points;
  }, [potentialData]);

  if (linePoints.length === 0) return null;

  return (
    <Line
      points={linePoints}
      color="red"
      lineWidth={2}
      transparent
      opacity={0.6}
    />
  );
}

// 主要的PIC可视化组件
const PICVisualization: React.FC<PICVisualizationProps> = ({ simulationData }) => {
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  
  useEffect(() => {
    if (!simulationData?.data?.frames) return;
    
    let interval: ReturnType<typeof setInterval>;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentFrame(prev => {
          const nextFrame = prev + 1;
          if (nextFrame >= simulationData.data.frames.length) {
            setIsPlaying(false);
            return 0;
          }
          return nextFrame;
        });
      }, 100); // 每100ms更新一帧
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPlaying, simulationData]);

  if (!simulationData?.data?.frames || simulationData.data.frames.length === 0) {
    return (
      <group>
        <mesh>
          <boxGeometry args={[1, 1, 1]} />
          <meshStandardMaterial color="gray" transparent opacity={0.3} />
        </mesh>
      </group>
    );
  }

  const frame = simulationData.data.frames[currentFrame];
  const beam1 = frame?.phase_space?.beam1;
  const beam2 = frame?.phase_space?.beam2;
  const fields = frame?.fields;

  return (
    <group>
      {/* 粒子束1 - 蓝色 */}
      {beam1 && (
        <ParticleCloud
          positions={beam1.positions}
          velocities={beam1.velocities}
          color="blue"
        />
      )}
      
      {/* 粒子束2 - 红色 */}
      {beam2 && (
        <ParticleCloud
          positions={beam2.positions}
          velocities={beam2.velocities}
          color="red"
        />
      )}
      
      {/* 电场可视化 */}
      {fields?.electric_field && (
        <ElectricFieldVisualization fieldData={fields.electric_field} />
      )}
      
      {/* 电势可视化 */}
      {fields?.potential && (
        <PotentialVisualization potentialData={fields.potential} />
      )}
      
      {/* 坐标轴 */}
      <Line points={[[-10, 0, 0], [10, 0, 0]]} color="white" lineWidth={1} />
      <Line points={[[0, -10, 0], [0, 10, 0]]} color="white" lineWidth={1} />
      
      {/* 播放控制UI（作为3D文本） */}
      <mesh position={[-8, 8, 0]}>
        <planeGeometry args={[3, 1]} />
        <meshBasicMaterial 
          color={isPlaying ? "green" : "gray"} 
          transparent 
          opacity={0.7}
        />
      </mesh>
    </group>
  );
};

export default PICVisualization;
