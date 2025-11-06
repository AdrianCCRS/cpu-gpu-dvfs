# HPC Cluster Capabilities Overview
**Project 10 — DVFS + ML for Heterogeneous CPU–GPU Systems**

This document summarizes the hardware capabilities and monitoring tools available on each compute node of the UIS HPC cluster.  
Generated from `detect_hardware_v2.py`.

---

## Cluster-Wide Comparison

| Feature | `felix.sc3.uis.edu.co` | `thor.uis.edu.co` | `guane04.uis.edu.co` | `yaje.uis.edu.co` |
|----------|------------------------|-------------------|-----------------------|-------------------|
| **CPU Model** | Xeon X7560 @ 2.27 GHz | Xeon E7-8867 v3 @ 2.50 GHz | Xeon E5645 @ 2.40 GHz | Xeon E5-2609 v3 @ 1.90 GHz |
| **Architecture** | Nehalem | Haswell-EP | Westmere | Haswell-EP |
| **Sockets** | 4 | 4 | 2 | 1 |
| **Cores per Socket** | 8 | 16 | 6 | 6 |
| **Threads per Core** | 2 | 2 | 2 | 1 |
| **Logical CPUs** | 64 | 128 | 24 | 6 |
| **DVFS Driver** | acpi-cpufreq | — | pcc-cpufreq | pcc-cpufreq |
| **Frequency Range (GHz)** | 1.06–2.26 | — | 1.6–2.4 | 1.2–1.9 |
| **RAPL (Energy Counters)** | Not available | Available (20 domains) | Not available | Available (5 domains) |
| **HWMon Sensors** | coretemp ×4 | coretemp ×4 | coretemp ×2 | coretemp ×1 |
| **NUMA Nodes** | 4 (~32 GB each) | 4 (~322 GB each) | 2 (~56+48 GB) | 1 (~48 GB) |
| **GPU** | 2× GTX TITAN X (12 GB) | 2× Tesla K20c (4.7 GB) | 8× Tesla M2050 (2.6 GB) | 1× GTX TITAN X (12 GB) |
| **GPU Driver** | 450.51.05 | 418.226.00 | 390.116 | 460.39 |
| **Key Tools** | nvidia-smi, cpupower, perf, turbostat, numactl | Same | Same | Same |
| **Best Use Case** | CPU-only or NUMA-aware workloads | Energy-aware CPU+GPU (RAPL + NVML) | Multi-GPU DVFS testing | Small-scale CPU–GPU co-tuning |

---

## Node: `felix.sc3.uis.edu.co`

| Feature | Details |
|----------|----------|
| **CPU** | Intel Xeon X7560 @ 2.27 GHz (4 sockets × 8 cores × 2 threads = 64 logical CPUs) |
| **Architecture** | Nehalem |
| **DVFS Driver** | `acpi-cpufreq` |
| **Frequency Range** | 1.06 – 2.26 GHz |
| **Governors** | conservative, userspace, powersave, ondemand, performance |
| **RAPL** | Not available |
| **HWMon** | `coretemp × 4` (one per socket) |
| **NUMA Nodes** | 4 (~32 GB each, local distance 10 / remote 20) |
| **GPU** | 2× GeForce GTX TITAN X (12 GB each, driver 450.51.05) |
| **Tools** | nvidia-smi, cpupower, perf, turbostat, numactl |
| **Best Use** | CPU-only or NUMA-aware experiments without energy counters |

---

## Node: `thor.uis.edu.co`

| Feature | Details |
|----------|----------|
| **CPU** | Intel Xeon E7-8867 v3 @ 2.50 GHz (4 × 16 × 2 = 128 logical CPUs) |
| **Architecture** | Haswell-EP |
| **DVFS Driver** | None (no cpufreq sysfs interface) |
| **RAPL** | Available (20 domains detected) |
| **HWMon** | `coretemp × 4` |
| **NUMA Nodes** | 4 (~322 GB each, local distance 10 / remote 21) |
| **GPU** | 2× Tesla K20c (4.7 GB each, driver 418.226.00) |
| **Tools** | Same as `felix` |
| **Best Use** | Energy-aware CPU+GPU DVFS experiments (RAPL + NVML) |

---

## Node: `guane04.uis.edu.co`

| Feature | Details |
|----------|----------|
| **CPU** | Intel Xeon E5645 @ 2.40 GHz (2 × 6 × 2 = 24 logical CPUs) |
| **Architecture** | Westmere |
| **DVFS Driver** | `pcc-cpufreq` |
| **Frequency Range** | 1.6 – 2.4 GHz |
| **RAPL** | Not available |
| **HWMon** | `coretemp × 2` |
| **NUMA Nodes** | 2 (~56 GB and ~48 GB, local distance 10 / remote 20) |
| **GPU** | 8× Tesla M2050 (2.6 GB each, driver 390.116) |
| **Tools** | nvidia-smi, cpupower, perf, turbostat, numactl |
| **Best Use** | Multi-GPU coordinated DVFS and throughput experiments |

---

## Node: `yaje.uis.edu.co`

| Feature | Details |
|----------|----------|
| **CPU** | Intel Xeon E5-2609 v3 @ 1.90 GHz (1 × 6 × 1 = 6 logical CPUs) |
| **Architecture** | Haswell-EP |
| **DVFS Driver** | `pcc-cpufreq` |
| **Frequency Range** | 1.2 – 1.9 GHz |
| **RAPL** | Available (5 domains) |
| **HWMon** | `coretemp × 1` |
| **NUMA Nodes** | 1 (uniform access, 48 GB) |
| **GPU** | 1× GeForce GTX TITAN X (12 GB, driver 460.39) |
| **Tools** | Same as above |
| **Best Use** | Small-scale CPU–GPU DVFS co-tuning experiments |

---

## System-Wide Tools and Their Roles

| Tool | Description | Project Role |
|------|--------------|---------------|
| **nvidia-smi** | NVIDIA System Management Interface. Monitors and controls GPU power, clock, and utilization. | GPU DVFS control and telemetry. |
| **rocm-smi** | AMD System Management Interface (not installed). | Would serve the same role for AMD GPUs. |
| **intel_gpu_top** | Real-time monitoring for Intel iGPUs (not applicable here). | — |
| **cpupower** | Adjusts CPU frequency and governors via cpufreq. | CPU DVFS manipulation. |
| **turbostat** | Reports per-core frequencies, power, and temperatures. | Fine-grained runtime monitoring. |
| **perf** | Performance counter tool (instructions, cache misses, IPC). | Feature collection for ML model. |
| **numactl** | Controls CPU/memory binding on NUMA systems. | NUMA locality control during benchmarks. |
| **ipmitool** | Interfaces with server management controllers (BMC) to measure total node power. | System-level energy fallback when RAPL absent. |
| **hwmon** | Kernel interface exposing temperature/voltage sensors. | Thermal feature input for ML. |
| **amd_uprof** | AMD CPU profiler (not installed, irrelevant for Intel). | — |
| **RAPL Interface** | `/sys/class/powercap/intel-rapl:*` files exposing energy in µJ. | Direct energy measurement for EDP computation. |
