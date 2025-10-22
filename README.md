# Proyecto 10: DVFS + ML for HPC Systems

**Dynamic Voltage and Frequency Scaling (DVFS) in Heterogeneous CPU–GPU Systems using Machine Learning**

## Objective

Design and implement a lightweight runtime system that uses machine learning models trained on execution metrics to dynamically adjust CPU and GPU frequencies in real-time, minimizing the Energy–Delay Product (EDP) for hybrid HPC applications.

## Project Structure

```
proyecto10/
├── data/                  # Experimental datasets (CSV format)
├── benchmarks/
│   ├── cpu/              # CPU microbenchmarks (dot product, memcpy)
│   └── gpu/              # GPU kernels (GEMM, stencil, SpMV)
├── scripts/
│   ├── detect_hardware.sh      # Hardware detection script
│   ├── run_benchmark.py        # Automated benchmarking with freq control
│   ├── measure_power.py        # Power measurement wrapper (RAPL, NVML)
│   └── generate_dataset.py     # Dataset generation and preprocessing
├── runtime/
│   ├── controller.py           # ML-based frequency controller (Python)
│   └── controller.cpp          # Alternative C++ implementation
├── models/
│   └── rf_model.joblib         # Trained ML models
├── notebooks/
│   └── analysis.ipynb          # Data analysis and visualization
├── docs/
│   ├── hardware_specs.md       # Hardware specifications
│   └── experiment_log.md       # Experiment logs and results
├── tests/
│   ├── test_benchmarks.py      # Unit tests for benchmarks
│   └── test_runtime.py         # Unit tests for runtime
├── configs/
│   └── experiment_config.yaml  # Experiment configuration
└── README.md
```

## Hardware Targets

- **Initial Platform**: Intel CPU (RAPL, cpufreq) + Intel Iris Xe GPU
- **Extended Platform**: HPC server with NVIDIA GPUs (NVML)

## Workloads

- **CPU Microbenchmarks**: dot product, memcpy
- **GPU Kernels**: small GEMM, 3D stencil, SpMV

## Key Technologies

- **CPU Control**: cpupower, sysfs (`/sys/devices/system/cpu/`)
- **CPU Energy**: RAPL (turbostat, perf, pyRAPL)
- **GPU Control/Measurement**: nvidia-smi, pynvml, intel_gpu_top
- **Performance Profiling**: perf stat
- **ML Libraries**: scikit-learn, XGBoost, optuna

## Workflow

1. **Hardware Detection**: Identify CPU/GPU capabilities
2. **Benchmark Implementation**: Validate CPU/GPU microbenchmarks
3. **Frequency Sweeps**: Automated frequency/input size exploration
4. **Data Collection**: Gather metrics (time, energy, performance counters)
5. **Feature Engineering**: Clean data and extract features
6. **Model Training**: Train Random Forest/XGBoost models
7. **Runtime Implementation**: Deploy ML-driven DVFS controller
8. **Evaluation**: Compare against baseline governors

## Dataset Schema

CSV columns: `timestamp`, `hostname`, `cpu_model`, `gpu_model`, `kernel_name`, `input_size`, `freq_cpu_MHz`, `freq_gpu_MHz`, `time_s`, `energy_J_cpu`, `energy_J_gpu`, `edp_Js`, `instructions`, `cycles`, `ipc`, `cache_misses`, `l1_misses`, `l2_misses`, `sm_util_percent`, `gpu_occupancy`, `run_id`

## Getting Started

### Prerequisites

```bash
# Install required tools
sudo apt-get install linux-tools-common linux-tools-generic cpupower

# Python dependencies
pip install pandas numpy scikit-learn xgboost joblib pynvml psutil
```

### Quick Start

1. Detect hardware capabilities:
   ```bash
   ./scripts/detect_hardware.sh
   ```

2. Run first benchmark:
   ```bash
   python scripts/run_benchmark.py --kernel dot --sizes 1000,10000,100000
   ```

3. Generate dataset:
   ```bash
   python scripts/generate_dataset.py --output data/experiments_$(date +%Y%m%d).csv
   ```

## Security Note

This project requires elevated privileges to modify CPU/GPU frequencies. On shared HPC systems, coordinate with administrators and respect usage policies.

## Reproducibility

- All experiments log commit SHA and model version
- Deterministic seeds for random processes
- Environment metadata saved with each dataset

## License

[To be determined]

## Authors

[Your name/team]

## Acknowledgments

Project developed at CAGE/HPC Lab.
