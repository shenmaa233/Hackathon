import json
import asyncio
import threading
import base64
import io
import os
from typing import Dict, Any
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from qwen_agent.tools.base import BaseTool, register_tool
from .pic.pic import (
    initial_loading, charge, poisson_equation_preparation, 
    solve_field_cpu, deposit_charge_kernel, push_particles_kernel
)
import cupy as cp
from scipy.sparse import spdiags, csc_matrix

@register_tool('pic_simulation')
class PICSimulation(BaseTool):
    """
    Particle-in-Cell (PIC) plasma simulation tool.
    Simulates plasma physics phenomena and generates real-time visualization data.
    """
    
    description = """
    Advanced Particle-in-Cell (PIC) plasma physics simulation tool. 
    Simulates electron beam interactions, plasma instabilities, and electromagnetic phenomena.
    Returns real-time simulation data for visualization including phase space, electric fields, and particle distributions.
    """
    
    parameters = [
        {
            'name': 'simulation_type',
            'type': 'string',
            'description': 'Type of simulation: "two_stream" (two electron beams), "single_beam" (single electron beam), "landau_damping" (plasma oscillations)',
            'required': True,
            'enum': ['two_stream', 'single_beam', 'landau_damping']
        },
        {
            'name': 'beam_velocity_1',
            'type': 'number',
            'description': 'Velocity of first electron beam (in units of thermal velocity)',
            'required': False,
            'default': 5.0
        },
        {
            'name': 'beam_velocity_2', 
            'type': 'number',
            'description': 'Velocity of second electron beam (in units of thermal velocity, use negative for counter-streaming)',
            'required': False,
            'default': -5.0
        },
        {
            'name': 'simulation_steps',
            'type': 'integer',
            'description': 'Number of simulation time steps to run',
            'required': False,
            'default': 1000
        },
        {
            'name': 'grid_size',
            'type': 'integer', 
            'description': 'Number of spatial grid points',
            'required': False,
            'default': 256
        }
    ]

    def __init__(self, tool_cfg=None):
        super().__init__(tool_cfg)
        self.simulation_data = {}
        self.is_running = False
        
    def call(self, params: str, **kwargs) -> str:
        """Execute PIC simulation with given parameters."""
        try:
            # Parse parameters
            if isinstance(params, str):
                params_dict = json.loads(params)
            else:
                params_dict = params
                
            simulation_type = params_dict.get('simulation_type', 'two_stream')
            beam_v1 = params_dict.get('beam_velocity_1', 5.0)
            beam_v2 = params_dict.get('beam_velocity_2', -5.0) 
            steps = params_dict.get('simulation_steps', 1000)
            grid_size = params_dict.get('grid_size', 256)
            
            # Run simulation
            result = self._run_simulation(
                simulation_type=simulation_type,
                beam_v1=beam_v1,
                beam_v2=beam_v2, 
                steps=steps,
                grid_size=grid_size
            )
            
            # 生成GIF动画
            gif_path = self._generate_gif_animation(result, simulation_type)
            
            # 为AI准备概览数据
            summary_data = {
                'frames_count': len(result["frames"]),
                'simulation_params': result['simulation_params'],
                'gif_url': f'http://localhost:8080/static/{os.path.basename(gif_path)}' if gif_path else None
            }
            
            return json.dumps({
                'success': True,
                'simulation_type': simulation_type,
                'message': f'PIC模拟完成！生成了{len(result["frames"])}帧数据。\n\n![PIC模拟动画]({summary_data["gif_url"]})\n\n模拟展示了{simulation_type}类型的等离子体现象。',
                'data': summary_data,
                'gif_url': summary_data["gif_url"]
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                'success': False,
                'error': str(e),
                'message': 'PIC simulation failed'
            }, ensure_ascii=False)
    
    def _run_simulation(self, simulation_type: str, beam_v1: float, beam_v2: float, 
                       steps: int, grid_size: int) -> Dict[str, Any]:
        """Run the actual PIC simulation."""
        
        # Simulation constants
        L = 64.0
        wp_e = 1.0
        Ng = grid_size
        dx = L / Ng
        dt = 0.1
        v_th = 1.0
        v_min = -15.0
        v_max = 15.0
        N_ions = 20000
        
        # Particle parameters based on simulation type
        if simulation_type == 'two_stream':
            N1, N2 = 10000, 10000
            v0_1, v0_2 = beam_v1, beam_v2
            re_1, re_2 = -1.0, -1.0
        elif simulation_type == 'single_beam':
            N1, N2 = 15000, 5000
            v0_1, v0_2 = beam_v1, 0.0
            re_1, re_2 = -1.0, -1.0
        else:  # landau_damping
            N1, N2 = 12000, 8000
            v0_1, v0_2 = 0.0, 0.0
            re_1, re_2 = -1.0, -1.0
        
        # Initialize particles
        xp1_cpu, vp1_cpu = initial_loading(N1, v0_1, v_th, v_min, v_max, 0.1, 1, L)
        xp2_cpu, vp2_cpu = initial_loading(N2, v0_2, v_th, v_min, v_max, 0.1, 1, L)
        
        # Transfer to GPU
        xp1, vp1 = cp.asarray(xp1_cpu), cp.asarray(vp1_cpu)
        xp2, vp2 = cp.asarray(xp2_cpu), cp.asarray(vp2_cpu)
        
        # Setup simulation
        Q1, Q2, rho_ions = charge(re_1, re_2, N_ions, N1, N2, L, wp_e)
        Ax = poisson_equation_preparation(Ng)
        
        # Storage for results
        frames = []
        save_interval = max(1, steps // 50)  # Save up to 50 frames
        
        threads_per_block = 256
        blocks_per_grid_N1 = (N1 + threads_per_block - 1) // threads_per_block
        blocks_per_grid_N2 = (N2 + threads_per_block - 1) // threads_per_block
        
        # Main simulation loop
        for it in range(steps):
            # Charge deposition
            rho_grid = cp.zeros(Ng, dtype=cp.float64)
            deposit_charge_kernel((blocks_per_grid_N1,), (threads_per_block,), 
                                (xp1, N1, Q1, dx, Ng, rho_grid))
            deposit_charge_kernel((blocks_per_grid_N2,), (threads_per_block,), 
                                (xp2, N2, Q2, dx, Ng, rho_grid))
            rho_grid += rho_ions
            
            # Solve Poisson equation
            rho_cpu = cp.asnumpy(rho_grid)
            Phi_cpu, Eg_cpu = solve_field_cpu(rho_cpu, Ng, dx, Ax)
            Eg = cp.asarray(Eg_cpu)
            
            # Push particles
            push_particles_kernel((blocks_per_grid_N1,), (threads_per_block,), 
                                (xp1, vp1, N1, Eg, re_1, dt, dx, Ng, L))
            push_particles_kernel((blocks_per_grid_N2,), (threads_per_block,), 
                                (xp2, vp2, N2, Eg, re_2, dt, dx, Ng, L))
            
            # Save frame data
            if it % save_interval == 0 or it == steps - 1:
                xp1_frame = cp.asnumpy(xp1)
                vp1_frame = cp.asnumpy(vp1)
                xp2_frame = cp.asnumpy(xp2)
                vp2_frame = cp.asnumpy(vp2)
                
                frame_data = {
                    'iteration': it,
                    'time': it * dt,
                    'phase_space': {
                        'beam1': {
                            'positions': xp1_frame.tolist(),
                            'velocities': vp1_frame.tolist()
                        },
                        'beam2': {
                            'positions': xp2_frame.tolist(), 
                            'velocities': vp2_frame.tolist()
                        }
                    },
                    'fields': {
                        'electric_field': Eg_cpu.tolist(),
                        'potential': Phi_cpu.tolist(),
                        'charge_density': rho_cpu.tolist()
                    },
                    'grid_info': {
                        'L': L,
                        'Ng': Ng,
                        'dx': dx
                    }
                }
                frames.append(frame_data)
        
        return {
            'frames': frames,
            'simulation_params': {
                'simulation_type': simulation_type,
                'beam_velocities': [beam_v1, beam_v2],
                'total_steps': steps,
                'grid_size': grid_size,
                'domain_length': L
            }
        }
    
    def _generate_gif_animation(self, simulation_data: Dict[str, Any], simulation_type: str) -> str:
        """生成PIC模拟的GIF动画"""
        try:
            frames = simulation_data['frames']
            if not frames:
                return None
            
            # 创建输出目录
            output_dir = '/home/shenmaa/codes/Hackathon/backend/static'
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成唯一文件名
            import time
            timestamp = int(time.time())
            gif_filename = f'pic_simulation_{simulation_type}_{timestamp}.gif'
            gif_path = os.path.join(output_dir, gif_filename)
            
            # 设置图形
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
            fig.suptitle(f'PIC模拟: {simulation_type}', fontsize=16)
            
            def animate(frame_idx):
                if frame_idx >= len(frames):
                    return
                    
                frame = frames[frame_idx]
                
                # 清除所有子图
                ax1.clear()
                ax2.clear()
                ax3.clear()
                ax4.clear()
                
                # 相空间图
                beam1_pos = np.array(frame['phase_space']['beam1']['positions'])
                beam1_vel = np.array(frame['phase_space']['beam1']['velocities'])
                beam2_pos = np.array(frame['phase_space']['beam2']['positions'])
                beam2_vel = np.array(frame['phase_space']['beam2']['velocities'])
                
                ax1.scatter(beam1_pos, beam1_vel, c='blue', alpha=0.6, s=1, label='束1')
                ax1.scatter(beam2_pos, beam2_vel, c='red', alpha=0.6, s=1, label='束2')
                ax1.set_xlabel('位置')
                ax1.set_ylabel('速度')
                ax1.set_title('相空间分布')
                ax1.legend()
                ax1.grid(True, alpha=0.3)
                
                # 位置分布
                ax2.hist(beam1_pos, bins=50, alpha=0.7, color='blue', label='束1')
                ax2.hist(beam2_pos, bins=50, alpha=0.7, color='red', label='束2')
                ax2.set_xlabel('位置')
                ax2.set_ylabel('粒子数')
                ax2.set_title('位置分布')
                ax2.legend()
                
                # 电场
                x_grid = np.linspace(0, frame['grid_info']['L'], len(frame['fields']['electric_field']))
                ax3.plot(x_grid, frame['fields']['electric_field'], 'g-', linewidth=2)
                ax3.set_xlabel('位置')
                ax3.set_ylabel('电场强度')
                ax3.set_title('电场分布')
                ax3.grid(True, alpha=0.3)
                
                # 电荷密度
                ax4.plot(x_grid, frame['fields']['charge_density'], 'm-', linewidth=2)
                ax4.set_xlabel('位置')
                ax4.set_ylabel('电荷密度')
                ax4.set_title('电荷密度分布')
                ax4.grid(True, alpha=0.3)
                
                # 添加时间信息
                fig.suptitle(f'PIC模拟: {simulation_type} (t={frame["time"]:.2f})', fontsize=16)
                
                plt.tight_layout()
            
            # 创建动画（选择部分帧以减少文件大小）
            frame_step = max(1, len(frames) // 30)  # 最多30帧
            selected_frames = list(range(0, len(frames), frame_step))
            
            anim = animation.FuncAnimation(
                fig, animate, frames=selected_frames, 
                interval=200, repeat=True, blit=False
            )
            
            # 保存GIF
            anim.save(gif_path, writer='pillow', fps=5, dpi=80)
            plt.close(fig)
            
            print(f"GIF已保存到: {gif_path}")
            return gif_path
            
        except Exception as e:
            print(f"生成GIF时出错: {e}")
            return None
