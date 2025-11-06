# ML Feature Set Specification — Proyecto 10
**DVFS Optimization via Machine Learning for Heterogeneous CPU–GPU Systems**

**Last Updated:** October 23, 2025  
**Version:** 1.0

---

## Overview

This document defines the complete feature set for training ML models (Random Forest, XGBoost) that predict optimal CPU and GPU frequencies to minimize Energy-Delay Product (EDP) in HPC heterogeneous workloads.

### Target Variables (What We Predict)
- **`freq_cpu_mhz`**: Optimal CPU frequency (MHz)
- **`freq_gpu_mhz`**: Optimal GPU frequency (MHz)
- **`edp_js`**: Energy-Delay Product (Joules × seconds) — used for labeling optimal configs

### Model Type
- **Regression** (predict continuous frequency values)
- **Classification** (predict frequency bin/class)
- **Multi-target** (predict CPU and GPU frequencies simultaneously)

---

## Feature Categories

### 1. System Context Features
### 2. Workload Characteristics Features
### 3. Hardware Utilization Features
### 4. Energy & Power Features
### 5. Performance Counters Features
### 6. Thermal Features
### 7. Memory Hierarchy Features
### 8. GPU-Specific Features
### 9. Historical/Temporal Features
### 10. Derived/Engineered Features

---

## Detailed Feature Definitions

| # | Feature Name | Type | Unit | Source | Category | Rationale |
|---|--------------|------|------|--------|----------|-----------|
| 1 | `timestamp` | datetime | ISO8601 | system clock | Context | Experiment reproducibility and temporal analysis |
| 2 | `run_id` | string | — | experiment script | Context | Unique identifier for each experimental run |
| 3 | `hostname` | categorical | — | `socket.gethostname()` | Context | Identify which cluster node (hardware differences) |
| 4 | `kernel_name` | categorical | — | experiment metadata | Workload | Type of computation (dot, gemm, stencil, spmv) affects optimal frequency |
| 5 | `input_size` | integer | elements | experiment config | Workload | Problem size dramatically affects CPU/GPU utilization and optimal frequency |
| 6 | `batch_size` | integer | — | experiment config | Workload | For iterative kernels; affects memory access patterns |
| 7 | `iterations` | integer | — | experiment config | Workload | Number of kernel invocations; affects amortized overhead |
| 8 | `cpu_model` | categorical | — | `detect_hardware_v2.py` | Context | Different CPUs have different frequency-efficiency curves |
| 9 | `gpu_model` | categorical | — | `nvidia-smi` / `detect_hardware_v2.py` | Context | Different GPUs have different power/performance characteristics |
| 10 | `num_cpu_cores` | integer | cores | `detect_hardware_v2.py` | Context | Available parallelism affects optimal frequency |
| 11 | `num_gpu_sms` | integer | SMs | `nvidia-smi` | Context | GPU compute capability affects frequency-performance scaling |
| 12 | `freq_cpu_mhz` | integer | MHz | cpufreq sysfs / `cpupower` | Context | **Independent variable**: CPU frequency being tested |
| 13 | `freq_gpu_mhz` | integer | MHz | `nvidia-smi` / NVML | Context | **Independent variable**: GPU frequency being tested |
| 14 | `freq_cpu_actual_mhz` | float | MHz | `/proc/cpuinfo` during run | Context | Actual achieved CPU frequency (may differ due to turbo/thermal) |
| 15 | `freq_gpu_actual_mhz` | float | MHz | `nvidia-smi --query-gpu=clocks.current.sm` | Context | Actual achieved GPU frequency |
| 16 | `governor` | categorical | — | cpufreq sysfs | Context | CPU governor in effect (performance, powersave, ondemand) |
| 17 | `time_s` | float | seconds | `time.time()` | Performance | **Primary target**: Execution time for EDP calculation |
| 18 | `energy_cpu_j` | float | joules | RAPL / hwmon / AMD uProf | Energy | CPU package energy consumption |
| 19 | `energy_gpu_j` | float | joules | NVML `power.draw` integral | Energy | GPU board energy consumption |
| 20 | `energy_total_j` | float | joules | `energy_cpu_j + energy_gpu_j` | Energy | Total system energy for EDP |
| 21 | `edp_js` | float | J·s | `energy_total_j * time_s` | **Target** | Energy-Delay Product — **objective to minimize** |
| 22 | `power_cpu_w` | float | watts | `energy_cpu_j / time_s` | Energy | Average CPU power during execution |
| 23 | `power_gpu_w` | float | watts | `energy_gpu_j / time_s` or NVML instant | Energy | Average GPU power during execution |
| 24 | `power_total_w` | float | watts | `power_cpu_w + power_gpu_w` | Energy | Total system power |
| 25 | `instructions` | integer | count | `perf stat -e instructions` | Performance | Total CPU instructions retired |
| 26 | `cycles` | integer | count | `perf stat -e cycles` | Performance | Total CPU cycles consumed |
| 27 | `ipc` | float | inst/cycle | `instructions / cycles` | Performance | Instructions per cycle — **key CPU efficiency metric** |
| 28 | `l1_dcache_misses` | integer | count | `perf stat -e L1-dcache-load-misses` | Memory | L1 data cache misses indicate memory bottleneck |
| 29 | `l2_cache_misses` | integer | count | `perf stat -e l2_rqsts.miss` | Memory | L2 cache misses |
| 30 | `l3_cache_misses` | integer | count | `perf stat -e LLC-load-misses` | Memory | Last-level cache misses (critical for frequency decision) |
| 31 | `cache_miss_rate` | float | % | `(l1 + l2 + l3 misses) / memory_refs * 100` | Memory | Overall cache efficiency |
| 32 | `branch_misses` | integer | count | `perf stat -e branch-misses` | Performance | Branch mispredictions affect pipeline efficiency |
| 33 | `branch_miss_rate` | float | % | `branch_misses / branches * 100` | Performance | Branch prediction accuracy |
| 34 | `stalled_cycles_frontend` | integer | count | `perf stat -e stalled-cycles-frontend` | Performance | CPU front-end stalls (fetch/decode bottleneck) |
| 35 | `stalled_cycles_backend` | integer | count | `perf stat -e stalled-cycles-backend` | Performance | CPU back-end stalls (execution/memory bottleneck) |
| 36 | `cpu_util_percent` | float | % | `psutil.cpu_percent()` or `perf` | Utilization | Overall CPU utilization (0-100%) |
| 37 | `cpu_util_per_core` | array[float] | % | per-core utilization | Utilization | Identify load imbalance across cores |
| 38 | `gpu_util_percent` | float | % | `nvidia-smi --query-gpu=utilization.gpu` | Utilization | GPU SM utilization (0-100%) |
| 39 | `gpu_mem_util_percent` | float | % | `nvidia-smi --query-gpu=utilization.memory` | Utilization | GPU memory controller utilization |
| 40 | `gpu_occupancy` | float | % | NVML `occupancy` or profiler | Utilization | Warp occupancy — **key GPU efficiency metric** |
| 41 | `sm_efficiency` | float | % | GPU profiler | Utilization | SM active cycles / total cycles |
| 42 | `memory_bandwidth_gbps` | float | GB/s | `perf stat -e mem_load_retired.l3_miss` × cache line | Memory | Achieved memory bandwidth |
| 43 | `memory_bandwidth_util` | float | % | `achieved / theoretical_max * 100` | Memory | Memory bandwidth utilization |
| 44 | `gpu_memory_bandwidth_gbps` | float | GB/s | `nvidia-smi dmon` or NVML | Memory | GPU memory bandwidth achieved |
| 45 | `temp_cpu_max_c` | float | °C | hwmon / `coretemp` | Thermal | Maximum CPU temperature across cores |
| 46 | `temp_cpu_avg_c` | float | °C | Average of all core temps | Thermal | Average CPU temperature |
| 47 | `temp_gpu_c` | float | °C | `nvidia-smi --query-gpu=temperature.gpu` | Thermal | GPU temperature |
| 48 | `thermal_throttling_cpu` | boolean | — | Check if freq < requested | Thermal | CPU thermal throttling occurred (invalidates run) |
| 49 | `thermal_throttling_gpu` | boolean | — | `nvidia-smi --query-gpu=clocks_throttle_reasons.*` | Thermal | GPU throttling occurred |
| 50 | `numa_node` | integer | — | `numactl` binding | Context | NUMA node where workload ran (affects memory latency) |
| 51 | `numa_local_memory_gb` | float | GB | Local node memory accesses | Memory | Memory locality affects optimal frequency |
| 52 | `numa_remote_memory_gb` | float | GB | Remote node memory accesses | Memory | Remote accesses are slower, may benefit from lower freq |
| 53 | `page_faults_major` | integer | count | `/proc/[pid]/stat` or `perf` | Memory | Major page faults (disk I/O) |
| 54 | `page_faults_minor` | integer | count | `/proc/[pid]/stat` or `perf` | Memory | Minor page faults (memory reclaim) |
| 55 | `context_switches` | integer | count | `perf stat -e context-switches` | Performance | Context switches indicate scheduling overhead |
| 56 | `gpu_compute_intensity` | float | flops/byte | Theoretical FLOPs / memory bytes | Workload | Compute-bound vs. memory-bound classification |
| 57 | `cpu_memory_intensity` | float | bytes/inst | Memory accesses / instructions | Workload | Memory-intensive workloads benefit from lower freq |
| 58 | `gpu_kernel_time_ms` | float | ms | CUDA event timers | Performance | Actual GPU kernel execution time |
| 59 | `gpu_memcpy_time_ms` | float | ms | CUDA event timers | Performance | PCIe transfer time (H2D + D2H) |
| 60 | `gpu_pcie_throughput_gbps` | float | GB/s | `memcpy_bytes / memcpy_time` | Memory | PCIe bottleneck indicator |
| 61 | `gpu_sm_active_cycles` | integer | count | NVML or profiler | Utilization | Cycles with at least one active warp |
| 62 | `gpu_sm_stall_percent` | float | % | Profiler metrics | Utilization | Percentage of cycles stalled (memory wait, etc.) |
| 63 | `gpu_warp_execution_efficiency` | float | % | Active threads / ideal threads | Utilization | Thread divergence metric |
| 64 | `gpu_global_load_efficiency` | float | % | Requested / actual global memory loads | Memory | Coalesced memory access efficiency |
| 65 | `gpu_global_store_efficiency` | float | % | Requested / actual global memory stores | Memory | Write coalescing efficiency |
| 66 | `gpu_shared_memory_usage_kb` | float | KB | per-SM shared memory used | Memory | Shared memory usage affects occupancy |
| 67 | `gpu_register_usage` | integer | regs/thread | Registers per thread | Utilization | High register usage limits occupancy |
| 68 | `turbo_enabled` | boolean | — | Check CPU capabilities | Context | Turbo boost can cause frequency variability |
| 69 | `hyperthreading_enabled` | boolean | — | `threads_per_core > 1` | Context | SMT affects CPU utilization interpretation |
| 70 | `rapl_available` | boolean | — | `detect_hardware_v2.py` | Context | Energy measurement reliability flag |
| 71 | `rapl_package_energy_j` | float | joules | RAPL package domain | Energy | Socket-level energy (more accurate than core-only) |
| 72 | `rapl_dram_energy_j` | float | joules | RAPL DRAM domain | Energy | Memory subsystem energy (if available) |
| 73 | `rapl_core_energy_j` | float | joules | RAPL core domain | Energy | Core-only energy |
| 74 | `rapl_uncore_energy_j` | float | joules | RAPL uncore domain | Energy | Uncore (cache, interconnect) energy |
| 75 | `amd_package_energy_j` | float | joules | AMD hwmon or uProf | Energy | AMD equivalent of RAPL package |
| 76 | `time_cpu_only_s` | float | seconds | Phase-specific timing | Performance | CPU-only phase duration |
| 77 | `time_gpu_only_s` | float | seconds | Phase-specific timing | Performance | GPU-only phase duration |
| 78 | `time_cpu_gpu_overlap_s` | float | seconds | Overlapping execution time | Performance | Concurrent CPU+GPU execution |
| 79 | `previous_freq_cpu_mhz` | integer | MHz | Historical from previous runs | Temporal | Previous configuration (for temporal models) |
| 80 | `previous_freq_gpu_mhz` | integer | MHz | Historical from previous runs | Temporal | Previous configuration |
| 81 | `previous_edp_js` | float | J·s | Historical from previous runs | Temporal | Previous EDP (reinforcement learning feedback) |
| 82 | `moving_avg_cpu_util` | float | % | Rolling average over N samples | Temporal | Smoothed CPU utilization trend |
| 83 | `moving_avg_gpu_util` | float | % | Rolling average over N samples | Temporal | Smoothed GPU utilization trend |
| 84 | `workload_phase` | categorical | — | Static analysis or runtime detection | Workload | Kernel phase (init, compute, memcpy, finalize) |
| 85 | `cpu_freq_normalized` | float | 0-1 | `(freq - min) / (max - min)` | Derived | Normalized CPU frequency for model input |
| 86 | `gpu_freq_normalized` | float | 0-1 | `(freq - min) / (max - min)` | Derived | Normalized GPU frequency |
| 87 | `edp_normalized` | float | 0-1 | Min-max scaled EDP | Derived | Normalized target for training |
| 88 | `ipc_efficiency` | float | ratio | `ipc / theoretical_max_ipc` | Derived | IPC relative to CPU's peak capability |
| 89 | `memory_boundedness` | float | 0-1 | `cache_miss_rate / threshold` | Derived | How memory-bound the workload is |
| 90 | `compute_boundedness` | float | 0-1 | `1 - memory_boundedness` | Derived | How compute-bound the workload is |
| 91 | `cpu_energy_efficiency` | float | J/inst | `energy_cpu_j / instructions` | Derived | Energy per instruction |
| 92 | `gpu_energy_efficiency` | float | J/op | `energy_gpu_j / gpu_operations` | Derived | Energy per GPU operation |
| 93 | `speedup_vs_baseline` | float | ratio | `time_baseline / time_s` | Derived | Performance relative to baseline frequency |
| 94 | `energy_savings_vs_baseline` | float | % | `(energy_baseline - energy_total_j) / energy_baseline * 100` | Derived | Energy savings vs. baseline |
| 95 | `edp_improvement_vs_baseline` | float | % | `(edp_baseline - edp_js) / edp_baseline * 100` | Derived | EDP improvement (target metric) |
| 96 | `freq_cpu_prev_delta_mhz` | integer | MHz | `freq_cpu_mhz - previous_freq_cpu_mhz` | Derived | Frequency change magnitude |
| 97 | `freq_gpu_prev_delta_mhz` | integer | MHz | `freq_gpu_mhz - previous_freq_gpu_mhz` | Derived | GPU frequency change magnitude |
| 98 | `cpu_gpu_freq_ratio` | float | ratio | `freq_cpu_mhz / freq_gpu_mhz` | Derived | Relative CPU-GPU frequency balance |
| 99 | `power_efficiency` | float | ops/watt | `throughput / power_total_w` | Derived | Performance per watt |
| 100 | `is_optimal_config` | boolean | — | `edp_js == min(edp) for workload` | **Target** | Binary label for classification: is this the best config? |

---

## Feature Importance Guidelines

### Critical Features (Must Have)
These features are essential for accurate predictions:

1. **Workload identification**: `kernel_name`, `input_size`
2. **Current frequencies**: `freq_cpu_mhz`, `freq_gpu_mhz`
3. **Performance metrics**: `time_s`, `ipc`, `cpu_util_percent`, `gpu_util_percent`
4. **Energy metrics**: `energy_cpu_j`, `energy_gpu_j`
5. **Target**: `edp_js` or `is_optimal_config`

### High-Value Features
These provide strong predictive power:

- **Memory hierarchy**: `l3_cache_misses`, `cache_miss_rate`, `memory_bandwidth_util`
- **GPU efficiency**: `gpu_occupancy`, `sm_efficiency`, `gpu_mem_util_percent`
- **Thermal**: `temp_cpu_avg_c`, `temp_gpu_c`, `thermal_throttling_*`
- **Derived metrics**: `ipc_efficiency`, `memory_boundedness`, `compute_boundedness`

### Nice-to-Have Features
Improve model but not strictly necessary:

- **Fine-grained perf counters**: `branch_misses`, `stalled_cycles_*`
- **NUMA**: `numa_local_memory_gb`, `numa_remote_memory_gb`
- **GPU profiling details**: `gpu_warp_execution_efficiency`, `gpu_global_*_efficiency`
- **Temporal features**: `previous_*`, `moving_avg_*`

### Optional/Advanced Features
For specialized analysis:

- **Phase detection**: `workload_phase`, `time_cpu_only_s`, `time_gpu_only_s`
- **Energy breakdown**: `rapl_dram_energy_j`, `rapl_uncore_energy_j`
- **Comparison metrics**: `speedup_vs_baseline`, `edp_improvement_vs_baseline`

---

## Data Collection Strategy

### Minimal Viable Dataset (MVP)

**Required Tools:**
- `cpupower` (CPU frequency control)
- `nvidia-smi` (GPU frequency + telemetry)
- `perf stat` (basic CPU counters)
- `time` command (execution time)
- RAPL or hwmon (energy)

**Features (20 columns):**
```csv
timestamp, run_id, hostname, kernel_name, input_size, cpu_model, gpu_model,
freq_cpu_mhz, freq_gpu_mhz, time_s, energy_cpu_j, energy_gpu_j, edp_js,
instructions, cycles, ipc, cpu_util_percent, gpu_util_percent,
temp_cpu_avg_c, temp_gpu_c
```

**Collection Command:**
```bash
# Pseudo-command
perf stat -e instructions,cycles \
  python run_experiment.py \
    --kernel dot --size 10000 --freq-cpu 2400 --freq-gpu 1200
```

### Full Feature Dataset (Research-Grade)

**Additional Tools:**
- `turbostat` (detailed CPU states)
- `numactl` (NUMA control)
- CUDA profiler (`nvprof` or `nsys`)
- AMD uProf (for AMD systems)

**Features:** All 100 features listed above

---

## Feature Engineering Recommendations

### 1. Normalization
```python
# Frequency normalization (0-1 range)
freq_cpu_normalized = (freq_cpu_mhz - cpu_min_mhz) / (cpu_max_mhz - cpu_min_mhz)

# EDP normalization (log scale often better)
edp_normalized = np.log1p(edp_js)  # or min-max scaling
```

### 2. One-Hot Encoding
```python
# Categorical features
kernel_name: [dot, gemm, stencil, spmv] → one-hot vectors
hostname: [felix, thor, guane04, yaje] → one-hot vectors
cpu_model: [X7560, E7-8867, E5645, E5-2609] → one-hot or label encoding
```

### 3. Interaction Features
```python
# Combine features for better predictions
cpu_gpu_balance = freq_cpu_mhz / freq_gpu_mhz
memory_compute_ratio = memory_bandwidth_util / cpu_util_percent
energy_delay_tradeoff = energy_total_j / time_s  # equivalent to power
```

### 4. Polynomial Features
```python
from sklearn.preprocessing import PolynomialFeatures

# Add quadratic terms for frequency effects
poly = PolynomialFeatures(degree=2, include_bias=False)
freq_features = poly.fit_transform([freq_cpu_mhz, freq_gpu_mhz])
# Creates: freq_cpu², freq_gpu², freq_cpu×freq_gpu
```

### 5. Dimensionality Reduction
```python
from sklearn.decomposition import PCA

# If you have 100+ features, reduce to top principal components
pca = PCA(n_components=20)
features_reduced = pca.fit_transform(features_normalized)
```

---

## Feature Collection Implementation

### Python Pseudocode

```python
import time
import subprocess
import json
from detect_hardware_v2 import HardwareDetectorV2

def collect_features(kernel_name, input_size, freq_cpu, freq_gpu, run_id):
    """
    Collect all features for one experimental run.
    
    Returns: dict with all feature values
    """
    features = {}
    
    # 1. Context features
    detector = HardwareDetectorV2()
    features['timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    features['run_id'] = run_id
    features['hostname'] = detector.info['metadata']['hostname']
    features['cpu_model'] = detector.info['cpu']['model']
    features['gpu_model'] = detector.info['gpu']['nvidia'][0]['name'] if detector.info['gpu']['nvidia'] else 'none'
    
    # 2. Workload features
    features['kernel_name'] = kernel_name
    features['input_size'] = input_size
    features['freq_cpu_mhz'] = freq_cpu
    features['freq_gpu_mhz'] = freq_gpu
    
    # 3. Set frequencies
    set_cpu_frequency(freq_cpu)  # using cpupower
    set_gpu_frequency(freq_gpu)  # using nvidia-smi
    
    # 4. Launch perf profiling
    perf_cmd = [
        'perf', 'stat',
        '-e', 'instructions,cycles,L1-dcache-load-misses,LLC-load-misses',
        '-e', 'branch-misses,stalled-cycles-frontend,stalled-cycles-backend',
        '-o', f'/tmp/perf_{run_id}.txt',
        '--',
        f'./benchmarks/{kernel_name}', str(input_size)
    ]
    
    # 5. Measure energy and time
    energy_cpu_start = read_rapl_energy()
    energy_gpu_start = read_gpu_energy()  # via NVML
    time_start = time.time()
    
    # 6. Run workload
    result = subprocess.run(perf_cmd, capture_output=True)
    
    time_end = time.time()
    energy_cpu_end = read_rapl_energy()
    energy_gpu_end = read_gpu_energy()
    
    # 7. Calculate performance metrics
    features['time_s'] = time_end - time_start
    features['energy_cpu_j'] = (energy_cpu_end - energy_cpu_start) / 1e6  # µJ to J
    features['energy_gpu_j'] = (energy_gpu_end - energy_gpu_start) / 1e6
    features['energy_total_j'] = features['energy_cpu_j'] + features['energy_gpu_j']
    features['edp_js'] = features['energy_total_j'] * features['time_s']
    
    # 8. Parse perf output
    perf_data = parse_perf_output(f'/tmp/perf_{run_id}.txt')
    features['instructions'] = perf_data['instructions']
    features['cycles'] = perf_data['cycles']
    features['ipc'] = perf_data['instructions'] / perf_data['cycles']
    features['l1_dcache_misses'] = perf_data.get('L1-dcache-load-misses', 0)
    features['l3_cache_misses'] = perf_data.get('LLC-load-misses', 0)
    features['branch_misses'] = perf_data.get('branch-misses', 0)
    features['stalled_cycles_frontend'] = perf_data.get('stalled-cycles-frontend', 0)
    features['stalled_cycles_backend'] = perf_data.get('stalled-cycles-backend', 0)
    
    # 9. GPU metrics via nvidia-smi
    gpu_stats = get_gpu_stats()  # query during run via separate thread
    features['gpu_util_percent'] = gpu_stats['utilization.gpu']
    features['gpu_mem_util_percent'] = gpu_stats['utilization.memory']
    features['temp_gpu_c'] = gpu_stats['temperature.gpu']
    features['freq_gpu_actual_mhz'] = gpu_stats['clocks.current.sm']
    
    # 10. CPU metrics
    features['cpu_util_percent'] = get_cpu_utilization()  # via psutil
    features['temp_cpu_avg_c'] = get_cpu_temperature()  # hwmon
    features['freq_cpu_actual_mhz'] = get_actual_cpu_freq()  # /proc/cpuinfo
    
    # 11. Derived features
    features['power_cpu_w'] = features['energy_cpu_j'] / features['time_s']
    features['power_gpu_w'] = features['energy_gpu_j'] / features['time_s']
    features['power_total_w'] = features['power_cpu_w'] + features['power_gpu_w']
    
    return features

# Usage
features = collect_features('dot', 10000000, 2400, 1200, 'run_001')
save_to_csv('dataset.csv', features)
```

---

## Dataset Format (CSV Example)

```csv
timestamp,run_id,hostname,kernel_name,input_size,cpu_model,gpu_model,freq_cpu_mhz,freq_gpu_mhz,time_s,energy_cpu_j,energy_gpu_j,edp_js,instructions,cycles,ipc,cpu_util_percent,gpu_util_percent,temp_cpu_avg_c,temp_gpu_c
2025-10-23T18:00:00Z,run_001,felix,dot,10000000,Xeon X7560,GTX TITAN X,2260,1200,0.523,45.2,32.1,40.4,5000000000,3200000000,1.56,85.3,72.1,62,58
2025-10-23T18:01:00Z,run_002,felix,dot,10000000,Xeon X7560,GTX TITAN X,1600,1200,0.687,28.3,33.5,42.4,5000000000,4800000000,1.04,68.2,74.8,54,59
...
```

---

## Feature Selection Process

### 1. Correlation Analysis
```python
import pandas as pd
import seaborn as sns

df = pd.read_csv('dataset.csv')
correlation = df.corr()

# High correlation with target (edp_js)
top_features = correlation['edp_js'].abs().sort_values(ascending=False).head(20)
print(top_features)

# Remove redundant features (high inter-correlation)
sns.heatmap(correlation[top_features.index], annot=True)
```

### 2. Feature Importance (Tree-Based)
```python
from sklearn.ensemble import RandomForestRegressor

X = df.drop(['edp_js', 'timestamp', 'run_id'], axis=1)
y = df['edp_js']

rf = RandomForestRegressor(n_estimators=100, random_state=42)
rf.fit(X, y)

# Get feature importance
importances = pd.DataFrame({
    'feature': X.columns,
    'importance': rf.feature_importances_
}).sort_values('importance', ascending=False)

print(importances.head(20))
```

### 3. Recursive Feature Elimination
```python
from sklearn.feature_selection import RFE

rfe = RFE(estimator=rf, n_features_to_select=20)
rfe.fit(X, y)

selected_features = X.columns[rfe.support_]
print("Selected features:", selected_features)
```

---

## Validation and Quality Checks

### Feature Quality Checklist

- [ ] **No missing values**: Use imputation or drop incomplete rows
- [ ] **No infinite values**: Check for division by zero
- [ ] **Reasonable ranges**: Validate frequencies, temperatures, energies
- [ ] **No constant features**: Remove features with zero variance
- [ ] **Scaling applied**: Normalize/standardize before training
- [ ] **No data leakage**: Future info not used to predict past
- [ ] **Balanced classes**: For classification, ensure class balance
- [ ] **Sufficient samples**: At least 10× features per sample

### Outlier Detection
```python
from scipy import stats

# Z-score method
z_scores = np.abs(stats.zscore(df[['time_s', 'energy_total_j', 'edp_js']]))
outliers = (z_scores > 3).any(axis=1)

print(f"Outliers detected: {outliers.sum()} / {len(df)}")
df_clean = df[~outliers]
```

---

## Expected Feature Importance Ranking (Hypothesis)

Based on DVFS+ML literature, we expect these features to be most important:

### Top 10 Expected Important Features

1. **`input_size`**: Problem size directly affects compute/memory balance
2. **`kernel_name`**: Different kernels have vastly different characteristics
3. **`ipc`**: Low IPC suggests memory-bound → lower freq beneficial
4. **`gpu_util_percent`**: Low GPU util → lower GPU freq saves energy
5. **`cache_miss_rate`**: High misses → memory-bound → freq reduction OK
6. **`freq_cpu_mhz`**: Direct input variable to model
7. **`freq_gpu_mhz`**: Direct input variable to model
8. **`memory_bandwidth_util`**: High util → memory bottleneck
9. **`gpu_occupancy`**: Low occupancy → GPU underutilized
10. **`cpu_util_percent`**: Low util → potential for freq reduction

### Feature Groups by Importance

**Tier 1 (Critical):**
- Workload: `kernel_name`, `input_size`
- Frequencies: `freq_cpu_mhz`, `freq_gpu_mhz`
- Performance: `time_s`, `ipc`

**Tier 2 (High value):**
- Memory: `cache_miss_rate`, `memory_bandwidth_util`
- GPU: `gpu_util_percent`, `gpu_occupancy`
- Energy: `energy_cpu_j`, `energy_gpu_j`

**Tier 3 (Useful):**
- Thermal: `temp_cpu_avg_c`, `temp_gpu_c`
- Derived: `memory_boundedness`, `compute_boundedness`
- Counters: `l3_cache_misses`, `branch_misses`

**Tier 4 (Context):**
- System: `cpu_model`, `gpu_model`, `hostname`
- Temporal: `previous_*`, `moving_avg_*`

---

## References and Best Practices

### Literature-Backed Feature Choices

1. **IPC and cache misses**: Proven predictors of frequency-performance scaling [Hsu & Feng, ISCA 2005]
2. **GPU occupancy**: Strong correlation with optimal GPU frequency [Leng et al., ISCA 2013]
3. **Memory bandwidth utilization**: Key for detecting memory-bound phases [Rountree et al., ICS 2009]
4. **EDP as target**: Standard metric for energy-performance tradeoff [Isci et al., MICRO 2006]

### Dataset Size Recommendations

- **Minimum**: 1000 samples (10 freq configs × 5 kernels × 4 sizes × 5 runs)
- **Recommended**: 5000-10000 samples
- **Ideal**: 50000+ samples (for deep learning models)

### Frequency Sweep Strategy

```python
# Example frequency space
cpu_freqs = [1200, 1600, 2000, 2400, 2800, 3200]  # MHz
gpu_freqs = [500, 700, 900, 1100, 1300, 1500]     # MHz

# Full factorial: 6 × 6 = 36 configs per workload
# With 5 kernels × 8 input sizes × 5 runs = 7200 experiments
```

---

## Implementation Roadmap

### Phase 1: MVP Dataset (Weeks 5-6)
- Collect 20 core features
- 1000 samples minimum
- Validate data quality
- Train initial RF model

### Phase 2: Full Feature Set (Weeks 7-8)
- Add all performance counters
- GPU profiling integration
- 5000+ samples
- Feature importance analysis

### Phase 3: Feature Engineering (Weeks 9-10)
- Derive interaction terms
- Temporal features
- Dimensionality reduction
- Model optimization

### Phase 4: Production Features (Weeks 11-12)
- Real-time feature extraction
- Low-overhead profiling
- Runtime integration

---

**Document Maintained By:** Proyecto 10 Team  
**For Questions:** Refer to experiment logs or hardware detection documentation  
**Version History:**
- v1.0 (2025-10-23): Initial comprehensive feature set definition
