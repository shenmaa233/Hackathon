import numpy as np
import cupy as cp
import matplotlib.pyplot as plt
from tqdm import tqdm
from scipy.sparse import spdiags, csc_matrix
from scipy.sparse.linalg import spsolve
import os

# Set print options for numpy
np.set_printoptions(threshold=np.inf)

# --------------------------------------------------------------------------
# INITIAL LOADING & UTILITY FUNCTIONS
# --------------------------------------------------------------------------

def maxwell_boltzman_dist_1D(v, v_0, v_th):
    """NumPy version for initial plotting checks."""
    n_0 = 1.0
    return ((n_0 / (np.sqrt(2 * np.pi) * v_th)) * np.exp(-((v - v_0) ** 2) / (2 * v_th ** 2)))

def maxwell_boltzman_dist_1D_cupy(v, v_0, v_th):
    """CuPy version for GPU calculations."""
    n_0 = 1.0
    return ((n_0 / (cp.sqrt(2 * cp.pi) * v_th)) * cp.exp(-((v - v_0) ** 2) / (2 * v_th ** 2)))

def acceptance_rejection_cupy(v_min, v_max, v_0, v_th, N):
    """Vectorized acceptance-rejection method on the GPU."""
    num_candidates = int(N * 3)
    accepted_speeds = cp.empty(0, dtype=cp.float64)
    
    while accepted_speeds.size < N:
        r_1 = cp.random.rand(num_candidates)
        v_candidates = v_min + r_1 * (v_max - v_min)
        f_max = maxwell_boltzman_dist_1D_cupy(v_0, v_0, v_th)
        r_2 = cp.random.rand(num_candidates)
        u_candidates = r_2 * f_max
        f_values = maxwell_boltzman_dist_1D_cupy(v_candidates, v_0, v_th)
        mask = u_candidates < f_values
        newly_accepted = v_candidates[mask]
        accepted_speeds = cp.concatenate((accepted_speeds, newly_accepted))

    return cp.asnumpy(accepted_speeds[:N])

def initial_loading(N, v_0, v_th, v_min, v_max, amplitude, mode, L):
    """Initializes particle positions and velocities."""
    position = np.linspace(0, L, N, dtype=np.float64)
    velocity = acceptance_rejection_cupy(v_min, v_max, v_0, v_th, N)
    if amplitude != 0:
        position = position + amplitude * np.cos(2 * np.pi * mode * position / L)
    return position, velocity

# --------------------------------------------------------------------------
# PLOTTING & SAVING FUNCTIONS
# --------------------------------------------------------------------------

def save_histogram_as_pdf(vp1, vp2, v0_1, v0_2, v_th, v_min, v_max, filename):
    fig, ax = plt.subplots()
    ax.hist(vp1, bins=30, ec="black", fc="blue", density=True, alpha=0.5, lw=1)
    x_1 = np.linspace(vp1.min(), vp1.max(), 1000)
    ax.plot(x_1, 2 * maxwell_boltzman_dist_1D(x_1, v0_1, v_th), color='black', linewidth=1)
    ax.hist(vp2, bins=30, ec="black", fc="red", density=True, alpha=0.5, lw=1)
    x_2 = np.linspace(vp2.min(), vp2.max(), 1000)
    ax.plot(x_2, 2 * maxwell_boltzman_dist_1D(x_2, v0_2, v_th), color='black', linewidth=1)
    ax.set_title('Superparticles Distribution for Speeds in 1D')
    ax.set_xlabel('$v$/$v_{th}$ (unitless)')
    ax.set_ylabel('$f(v//v_{th})$ (unitless)')
    ax.axis([v_min, v_max, 0, 2 * 0.19945547892115006])
    fig.savefig(filename)
    plt.close(fig)

def save_scatter_as_pdf(xp1, vp1, xp2, vp2, L, filename):
    fig, ax = plt.subplots()
    ax.scatter(xp1, vp1, s=0.1, color='blue', alpha=0.5)
    ax.scatter(xp2, vp2, s=0.1, color='red', alpha=0.5)
    ax.axis([0, L, -15, 15])
    ax.set_xlabel('$x$/$\lambda_{D}$ (unitless)')
    ax.set_ylabel('$v$/$v_{th}$ (unitless)')
    ax.set_title('Phase Space')
    fig.savefig(filename)
    plt.close(fig)

def save_subplot_as_pdf(ax, filename, legend=False):
    fig, new_ax = plt.subplots()
    new_ax.set_xlim(ax.get_xlim())
    new_ax.set_ylim(ax.get_ylim())
    new_ax.set_title(ax.get_title())
    new_ax.set_xlabel(ax.get_xlabel())
    new_ax.set_ylabel(ax.get_ylabel())
    for line in ax.get_lines():
        new_ax.plot(line.get_xdata(), line.get_ydata(), label=line.get_label(), color=line.get_color(), linewidth=line.get_linewidth())
    if legend:
        new_ax.legend()
    fig.savefig(filename)
    plt.close(fig)

# --------------------------------------------------------------------------
# CORE PIC FUNCTIONS (Using CuPy RawKernels)
# --------------------------------------------------------------------------

deposit_charge_kernel = cp.RawKernel(r'''
extern "C" __global__
void deposit_charge_kernel(const double* positions, int N, double charge_per_particle, double dx, int Ng, double* rho_grid) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        double pos = positions[idx];
        int grid_idx = round(pos / dx);
        grid_idx = (grid_idx % Ng + Ng) % Ng;
        atomicAdd(&rho_grid[grid_idx], charge_per_particle / dx);
    }
}
''', 'deposit_charge_kernel')

push_particles_kernel = cp.RawKernel(r'''
extern "C" __global__
void push_particles_kernel(double* xp, double* vp, int N, const double* Eg, double re, double dt, double dx, int Ng, double L) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        double pos = xp[idx];
        int grid_idx = round(pos / dx);
        grid_idx = (grid_idx % Ng + Ng) % Ng;
        double E_particle = Eg[grid_idx];
        vp[idx] += re * E_particle * dt;
        double new_pos = xp[idx] + vp[idx] * dt;
        new_pos = fmod(new_pos, L);
        if (new_pos < 0) { new_pos += L; }
        xp[idx] = new_pos;
    }
}
''', 'push_particles_kernel')


def charge(re_1, re_2, N_ions, N1, N2, L, wp_e):
    """Calculates particle charges and background density."""
    Q_1 = (wp_e**2 * L) / (N1 * re_1)
    if re_2 > 0: Q_2 = -Q_1 * (N1 / N2)
    elif re_2 < 0: Q_2 = Q_1 * (N1 / N2)
    else: Q_2 = 0
    rho_ions = (-Q_1 / L) * N_ions
    return Q_1, Q_2, rho_ions

def poisson_equation_preparation(Ng):
    """Prepares the sparse matrix for the CPU Poisson solver."""
    un = np.ones(Ng - 1)
    Ax = spdiags([un, -2 * un, un], [-1, 0, 1], Ng - 1, Ng - 1)
    return csc_matrix(Ax)

def solve_field_cpu(charge_density_cpu, Ng, dx, Ax):
    """Solves Poisson's equation on the CPU."""
    charge_density_cpu = charge_density_cpu[:Ng-1]
    Phi = spsolve(Ax, -charge_density_cpu * dx**2)
    Phi = np.append(Phi, 0)
    Eg = (np.roll(Phi, 1) - np.roll(Phi, -1)) / (2 * dx)
    return Phi, Eg

# --------------------------------------------------------------------------
# MAIN SIMULATION
# --------------------------------------------------------------------------

def main():
    ### Simulation Constants ###
    L = 64.0
    wp_e = 1.0
    Ng = 256
    dx = L / Ng
    Nt = 16000
    dt = 0.1
    v_th = 1.0
    v_min = -15.0
    v_max = 15.0
    N_ions = 20000

    # Beam parameters
    N1 = 10000
    v0_1 = 5.0
    re_1 = -1.0
    N2 = 10000
    v0_2 = -5.0
    re_2 = -1.0
    
    plot_interval = 200 # 每 200 步更新一次图像
    save_iterations = {0, 105, 152, 3500} # 在这些特定步骤保存图像
    output_dir = 'gpu'
    os.makedirs(output_dir, exist_ok=True)
    
    print("0. Initializing particles...")
    xp1_cpu, vp1_cpu = initial_loading(N1, v0_1, v_th, v_min, v_max, 0, 0, L)
    xp2_cpu, vp2_cpu = initial_loading(N2, v0_2, v_th, v_min, v_max, 0, 0, L)

    print("1. Transferring data to GPU...")
    xp1, vp1 = cp.asarray(xp1_cpu), cp.asarray(vp1_cpu)
    xp2, vp2 = cp.asarray(xp2_cpu), cp.asarray(vp2_cpu)

    Q1, Q2, rho_ions = charge(re_1, re_2, N_ions, N1, N2, L, wp_e)
    Ax = poisson_equation_preparation(Ng)
    
    E_kin_gpu = cp.zeros(Nt, dtype=cp.float64)
    E_pot_gpu = cp.zeros(Nt, dtype=cp.float64)
    time = np.arange(0, Nt * dt, dt)
    
    threads_per_block = 256
    blocks_per_grid_N1 = (N1 + threads_per_block - 1) // threads_per_block
    blocks_per_grid_N2 = (N2 + threads_per_block - 1) // threads_per_block

    # --- 初始化绘图窗口 ---
    fig, axs = plt.subplots(2, 3, figsize=(15, 9))
    plt.subplots_adjust(hspace=0.4, wspace=0.4)

    print("2. Starting main simulation loop...")
    for it in tqdm(range(Nt)):
        rho_grid = cp.zeros(Ng, dtype=cp.float64)
        deposit_charge_kernel((blocks_per_grid_N1,), (threads_per_block,), (xp1, N1, Q1, dx, Ng, rho_grid))
        deposit_charge_kernel((blocks_per_grid_N2,), (threads_per_block,), (xp2, N2, Q2, dx, Ng, rho_grid))
        rho_grid += rho_ions
        
        rho_cpu = cp.asnumpy(rho_grid)
        Phi_cpu, Eg_cpu = solve_field_cpu(rho_cpu, Ng, dx, Ax)
        Eg = cp.asarray(Eg_cpu)

        push_particles_kernel((blocks_per_grid_N1,), (threads_per_block,), (xp1, vp1, N1, Eg, re_1, dt, dx, Ng, L))
        push_particles_kernel((blocks_per_grid_N2,), (threads_per_block,), (xp2, vp2, N2, Eg, re_2, dt, dx, Ng, L))
        
        E_kin_gpu[it] = 0.5 * cp.abs(Q1 / re_1) * cp.sum(vp1**2) + 0.5 * cp.abs(Q2 / re_2) * cp.sum(vp2**2)
        E_pot_gpu[it] = 0.5 * cp.sum(Eg**2) * dx

        if it % plot_interval == 0 or it in save_iterations or it == Nt - 1:
            # --- 从 GPU 传回 CPU ---
            xp1_p, vp1_p = cp.asnumpy(xp1), cp.asnumpy(vp1)
            xp2_p, vp2_p = cp.asnumpy(xp2), cp.asnumpy(vp2)
            Phi_p, Eg_p = Phi_cpu, Eg_cpu
            rhot_p = rho_cpu
            E_kin_p, E_pot_p = cp.asnumpy(E_kin_gpu), cp.asnumpy(E_pot_gpu)

            # --- 绘图窗口 ---
            fig.suptitle(f'Simulation Plots - Iteration {it}', fontsize=16)

            # 速度分布图
            axs[0, 0].cla()
            axs[0, 0].hist(vp1_p, bins=30, ec="black", fc="blue", density=True, alpha=0.5, lw=1)
            axs[0, 0].hist(vp2_p, bins=30, ec="black", fc="red", density=True, alpha=0.5, lw=1)
            axs[0, 0].set_title('Velocity Distribution')
            axs[0, 0].set_xlabel('$v$/$v_{th}$')
            axs[0, 0].axis([v_min, v_max, 0, 0.4])

            # 相空间图
            axs[0, 1].cla()
            axs[0, 1].scatter(xp1_p, vp1_p, s=0.1, color='blue', alpha=0.5)
            axs[0, 1].scatter(xp2_p, vp2_p, s=0.1, color='red', alpha=0.5)
            axs[0, 1].axis([0, L, -15, 15])
            axs[0, 1].set_title('Phase Space')
            axs[0, 1].set_xlabel('$x$/$\lambda_{D}$')

            # 电势图
            axs[1, 1].cla()
            axs[1, 1].plot(Phi_p, color='orangered', linewidth=1)
            axs[1, 1].set_title('Electric Potential')
            axs[1, 1].set_xlabel('$x$/$\lambda_{D}$')

            # 能量演化图
            axs[0, 2].cla()
            axs[0, 2].plot(time[:it+1], E_kin_p[:it+1], color='yellowgreen', label='Kinetic', linewidth=1)
            axs[0, 2].plot(time[:it+1], E_pot_p[:it+1], color='orange', label='Potential', linewidth=1)
            axs[0, 2].set_xlim([0, Nt * dt])
            axs[0, 2].legend()
            axs[0, 2].set_title('Energy Evolution')
            axs[0, 2].set_xlabel('$\omega_{p,e}t$')

            # 电场图
            axs[1, 0].cla()
            axs[1, 0].plot(Eg_p, color='royalblue', linewidth=1)
            axs[1, 0].set_title('Electric Field')
            axs[1, 0].set_xlabel('$x$/$\lambda_{D}$')

            # 电荷密度图
            axs[1, 2].cla()
            axs[1, 2].plot(rhot_p, color='tomato', linewidth=1)
            axs[1, 2].set_title('Charge Density')
            axs[1, 2].set_xlabel('$x$/$\lambda_{D}$')
            
            plt.pause(0.001)

            # --- 保存特定帧的图像 ---
            if it in save_iterations:
                print(f"\nSaving plots for iteration {it}...")
                save_histogram_as_pdf(vp1_p, vp2_p, v0_1, v0_2, v_th, v_min, v_max, os.path.join(output_dir, f'dist_{it}.pdf'))
                save_scatter_as_pdf(xp1_p, vp1_p, xp2_p, vp2_p, L, os.path.join(output_dir, f'phase_space_{it}.pdf'))
                save_subplot_as_pdf(axs[1, 1], os.path.join(output_dir, f'potential_{it}.pdf'))
                save_subplot_as_pdf(axs[0, 2], os.path.join(output_dir, f'energy_{it}.pdf'), True)
                save_subplot_as_pdf(axs[1, 0], os.path.join(output_dir, f'efield_{it}.pdf'))
                save_subplot_as_pdf(axs[1, 2], os.path.join(output_dir, f'rho_{it}.pdf'))

    print("Simulation finished.")
    plt.show()

if __name__ == '__main__':
    main()
