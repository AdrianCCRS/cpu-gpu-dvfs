# Hardware Detector v2 — Specification Document

**Project:** Proyecto 10 — DVFS + ML Runtime for Heterogeneous HPC Systems  
**Version:** 2.0  
**Last Updated:** October 23, 2025

---

## Purpose and Scope

The Hardware Detector v2 is a **read-only**, **non-intrusive** Python utility designed for audit-only execution on HPC cluster nodes and developer workstations. It performs comprehensive hardware topology and capability detection without requiring elevated privileges or attempting any system modifications.

### Key Objectives

1. **Reproducibility**: Generate versioned JSON reports that can be included with experiment datasets to document the exact hardware configuration used.
2. **Portability**: Work across CentOS 7 HPC clusters and Fedora development machines with Python 2.7+ and 3.x compatibility.
3. **Safety**: Never attempt privileged operations; gracefully handle permission errors and record capability flags instead.
4. **Completeness**: Detect CPU, GPU, NUMA topology, energy monitoring capabilities, and available profiling tools.

### Design Principles

- **Defensive programming**: All external calls wrapped in try/except; timeouts on commands
- **Graceful degradation**: Missing tools or permissions result in flags, not failures
- **Standards compliance**: Uses well-known sysfs paths and standard Linux utilities
- **Zero configuration**: Works out-of-the-box on supported systems

---

## JSON Schema Specification

### Top-Level Structure

```json
{
  "schema_version": "2.0",
  "timestamp": "ISO8601 UTC timestamp",
  "metadata": { ... },
  "system": { ... },
  "cpu": { ... },
  "numa": { ... },
  "gpu": { ... },
  "hwmon": { ... },
  "capabilities": { ... },
  "warnings": [ ... ]
}
```

### Field Definitions

#### `schema_version` (string)
Version of the JSON schema. Current: `"2.0"`. Increment when incompatible changes are made.

#### `timestamp` (string)
UTC timestamp in ISO 8601 format (e.g., `"2025-10-23T14:30:00Z"`).

#### `metadata` (object)
```json
{
  "hostname": "string - system hostname",
  "os": "string - operating system (Linux, etc.)",
  "distribution": "string - distro name and version",
  "kernel": "string - kernel version",
  "python_version": "string - Python interpreter version",
  "uname_full": "string - full uname -a output"
}
```

**Purpose**: Provides system identification and reproducibility metadata.

#### `system` (object)
```json
{
  "arch": "string - architecture (x86_64, aarch64, etc.)",
  "uname": "tuple - platform.uname() output"
}
```

#### `cpu` (object)
```json
{
  "vendor": "string - Intel|AMD|ARM|etc.",
  "vendor_id": "string - raw vendor ID string",
  "model": "string - CPU model name",
  "logical_cpus": "int - total logical CPUs",
  "sockets": "int - number of sockets",
  "cores_per_socket": "int - physical cores per socket",
  "threads_per_core": "int - SMT threads per core",
  
  "freq": {
    "driver": "string - cpufreq driver (intel_pstate, acpi-cpufreq, amd-pstate)",
    "available_governors": ["array of strings"],
    "available_frequencies": ["array of int - frequencies in kHz"],
    "min_khz": "int - minimum frequency",
    "max_khz": "int - maximum frequency",
    "note": "string - optional note if cpufreq unavailable"
  },
  
  "rapl": {
    "available": "bool - RAPL domains present in /sys/class/powercap",
    "readable": "bool - energy counters readable by current user",
    "domains": ["array of strings - paths to energy_uj files"]
  },
  
  "amd_energy": {
    "available": "bool - AMD energy sensors detected in hwmon",
    "readable": "bool - sensors readable by current user",
    "sensors": ["array of strings - paths to energy*_input files"],
    "driver": "string - hwmon driver name (k10temp, zenpower, etc.)"
  },
  
  "amd_uprof": {
    "installed": "bool - AMD uProf toolset detected",
    "version": "string - uProf version if detectable",
    "path": "string - path to AMDuProfCLI executable",
    "msr_available": "bool - MSR device readable (required for advanced profiling)",
    "capabilities": ["array of strings - available profiling features"]
  }
}
```

**Units**:
- Frequencies: kHz (kilohertz)
- Energy files return microjoules (µJ)

**Intel RAPL Notes**:
- Requires `intel-rapl` kernel module loaded
- Typical domains: `package-0`, `core`, `uncore`, `dram`, `psys`
- Reading requires either root or `CAP_SYS_RAWIO`, or udev rules allowing read access
- Accuracy: ±5% typical, sampled at ~1ms intervals

**AMD Energy Notes**:
- Uses hwmon interface: `k10temp`, `zenpower`, `fam*` drivers
- Less fine-grained than Intel RAPL (package-level only on older generations)
- Zen3+ provides per-core energy counters via AMD uProf

**AMD uProf**:
- **Essential tool for AMD systems**: Provides detailed energy, power, and performance profiling
- Installation: Download from [AMD Developer Central](https://developer.amd.com/amd-uprof/)
- Typical install locations: `/opt/AMDuProf_*/` or `/usr/local/AMDuProf_*/`
- Capabilities detected:
  - `energy_profiling`: Per-core and package energy counters
  - `pmu_counters`: Performance monitoring unit events
  - `instruction_profiling`: IPC, branch prediction, cache analysis
  - `power_profiling`: Real-time power consumption tracking
- **MSR access required**: Most advanced features need `/dev/cpu/*/msr` readable
- Recommended for:
  - Zen2+ architectures (EPYC Rome, Ryzen 3000+)
  - Fine-grained per-CCD energy measurements
  - When hwmon provides insufficient granularity

#### `numa` (object)
```json
{
  "numactl_hw": "string - raw numactl --hardware output",
  "num_nodes": "int - number of NUMA nodes",
  "node_cpus": {
    "node_0": "string - CPU list (e.g., '0-15,32-47')",
    "node_1": "string - CPU list"
  },
  "note": "string - if numactl not installed"
}
```

**Interpretation**:
- Single-node systems have `num_nodes: 1` or field absent
- Multi-socket systems typically have one NUMA node per socket
- CPU lists use kernel format: ranges (0-7) and comma-separated values

#### `gpu` (object)
```json
{
  "nvidia": [
    {
      "name": "string - GPU model name",
      "memory": "string - total memory (e.g., '40960 MiB')",
      "driver": "string - driver version",
      "minor": "string - device minor number"
    }
  ],
  "amd": [
    {
      "rocm_smi": "string - product name from rocm-smi"
    }
  ],
  "intel": [
    {
      "card": "string - DRM card name (e.g., 'card0')",
      "freq_cur_mhz": "int - current frequency in MHz",
      "freq_min_mhz": "int - minimum frequency",
      "freq_max_mhz": "int - maximum frequency"
    }
  ]
}
```

**NVIDIA Notes**:
- Requires `nvidia-smi` and NVIDIA drivers installed
- Use `nvidia-smi` or `pynvml` for detailed telemetry (power, clocks, utilization)
- NVML API provides programmatic access to all metrics

**AMD Notes**:
- Requires ROCm stack and `rocm-smi` installed
- Use `rocm-smi` for detailed GPU metrics
- HIP runtime provides GPU profiling capabilities

**Intel Notes**:
- Integrated GPUs (Iris Xe, UHD) visible via `/sys/class/drm/card*/`
- Frequencies in MHz (read from `gt/rps/*` sysfs nodes)
- `intel_gpu_top` provides real-time monitoring (if installed)

#### `hwmon` (object)
```json
{
  "readable": "bool - at least one sensor readable",
  "sensors": [
    {
      "device": "string - hwmon device name (e.g., 'hwmon0')",
      "name": "string - sensor name (e.g., 'coretemp', 'k10temp')",
      "temps": ["array - temperature input files (e.g., 'temp1_input')"],
      "power": ["array - power input files (e.g., 'power1_input')"]
    }
  ]
}
```

**Units**:
- Temperature: millidegrees Celsius (m°C) — divide by 1000 for °C
- Power: microwatts (µW) — divide by 1,000,000 for watts

**Common Sensors**:
- `coretemp`: Intel per-core temperatures
- `k10temp`: AMD Zen CPU temperatures
- `nvme`: NVMe SSD temperatures
- `acpitz`: ACPI thermal zones

#### `capabilities` (object)
```json
{
  "tools": {
    "perf": "bool",
    "cpupower": "bool",
    "turbostat": "bool",
    "numactl": "bool",
    "nvidia-smi": "bool",
    "rocm-smi": "bool",
    "intel_gpu_top": "bool",
    "ipmitool": "bool"
  },
  "permissions": {
    "is_root": "bool - running as root",
    "can_write_cpufreq": "bool - can modify CPU frequencies"
  },
  "rapl_readable": "bool - RAPL energy counters readable",
  "amd_energy_readable": "bool - AMD energy sensors readable",
  "hwmon_readable": "bool - hwmon sensors readable",
  "ipmitool": "bool - IPMI available for BMC telemetry"
}
```

**Tool Purposes**:
- `perf`: CPU performance counters (cycles, instructions, cache misses)
- `cpupower`: CPU frequency manipulation and monitoring
- `turbostat`: Detailed CPU power/frequency state monitoring
- `numactl`: NUMA topology info and memory binding
- `nvidia-smi`: NVIDIA GPU management and monitoring
- `rocm-smi`: AMD GPU management and monitoring
- `intel_gpu_top`: Intel GPU real-time monitoring
- `ipmitool`: Out-of-band BMC access (node power, temperatures)

#### `warnings` (array of strings)
Actionable recommendations based on detected configuration issues.

**Examples**:
```json
[
  "RAPL not readable: Intel energy counters unavailable. Consider running as root or adjusting permissions.",
  "perf not found: install linux-tools for CPU profiling capabilities.",
  "Multi-socket system detected but numactl not installed. Install numactl for NUMA awareness."
]
```

---

## Sample JSON Output (AMD System)

### AMD EPYC with uProf

```json
{
  "schema_version": "2.0",
  "timestamp": "2025-10-23T19:00:00Z",
  "metadata": {
    "hostname": "amd-epyc-node",
    "os": "Linux",
    "distribution": "CentOS Linux 7.9.2009",
    "kernel": "3.10.0-1160.el7.x86_64",
    "python_version": "2.7.5",
    "uname_full": "Linux amd-epyc-node 3.10.0-1160.el7.x86_64 #1 SMP x86_64 GNU/Linux"
  },
  "system": {
    "arch": "x86_64"
  },
  "cpu": {
    "vendor": "AMD",
    "vendor_id": "AuthenticAMD",
    "model": "AMD EPYC 7763 64-Core Processor",
    "logical_cpus": 128,
    "sockets": 1,
    "cores_per_socket": 64,
    "threads_per_core": 2,
    "freq": {
      "driver": "acpi-cpufreq",
      "available_governors": ["performance", "powersave", "ondemand"],
      "available_frequencies": [2450000, 2250000, 2000000, 1500000],
      "min_khz": 1500000,
      "max_khz": 3500000
    },
    "rapl": {
      "available": false,
      "readable": false,
      "domains": []
    },
    "amd_energy": {
      "available": true,
      "readable": true,
      "sensors": [
        "/sys/class/hwmon/hwmon0/energy1_input"
      ],
      "driver": "k10temp"
    },
    "amd_uprof": {
      "installed": true,
      "version": "AMD uProf 4.0.389",
      "path": "/opt/AMDuProf_4.0-389/bin/AMDuProfCLI",
      "msr_available": true,
      "capabilities": [
        "energy_profiling",
        "pmu_counters",
        "instruction_profiling",
        "power_profiling"
      ]
    }
  },
  "numa": {
    "num_nodes": 8,
    "node_cpus": {
      "node_0": "0-7,64-71",
      "node_1": "8-15,72-79",
      "node_2": "16-23,80-87",
      "node_3": "24-31,88-95",
      "node_4": "32-39,96-103",
      "node_5": "40-47,104-111",
      "node_6": "48-55,112-119",
      "node_7": "56-63,120-127"
    }
  },
  "gpu": {
    "nvidia": [],
    "amd": [],
    "intel": []
  },
  "hwmon": {
    "readable": true,
    "sensors": [
      {
        "device": "hwmon0",
        "name": "k10temp",
        "temps": ["temp1_input", "temp2_input"],
        "power": ["energy1_input"]
      }
    ]
  },
  "capabilities": {
    "tools": {
      "perf": true,
      "cpupower": true,
      "turbostat": false,
      "numactl": true,
      "nvidia-smi": false,
      "rocm-smi": false,
      "intel_gpu_top": false,
      "ipmitool": true
    },
    "permissions": {
      "is_root": false,
      "can_write_cpufreq": false
    },
    "rapl_readable": false,
    "amd_energy_readable": true,
    "hwmon_readable": true,
    "ipmitool": true
  },
  "warnings": []
}
```

---

## Limitations and Caveats

### RAPL Energy Measurement

**Accuracy Issues**:
- **Thermal throttling**: Power readings drop during throttling; may not reflect true application behavior
- **Turbo Boost**: Turbo states can cause frequency/power variability
- **Idle power**: RAPL includes package idle power; must subtract baseline
- **DRAM domain**: Not available on all Intel CPUs (server Xeon only)

**Best Practices**:
- Use RAPL for *relative* comparisons, not absolute energy accounting
- Subtract idle baseline measured before experiments
- Average over multiple runs to account for variability
- Consider external power meters for ground truth validation

### AMD Energy Monitoring

**Generation Differences**:
- **Pre-Zen3**: Package-level energy only via `k10temp`
- **Zen3+**: Per-CCD energy counters available
- **EPYC Milan+**: More granular RAPL-like domains

**hwmon vs AMD uProf**:

| Feature | hwmon (k10temp/zenpower) | AMD uProf |
|---------|-------------------------|-----------|
| Installation | Kernel module (usually built-in) | Separate download required |
| Granularity | Package-level | Per-core, per-CCD |
| Sampling rate | ~1 second | Configurable (ms-level) |
| Privileges | Read-only access to sysfs | MSR access (root or capabilities) |
| Overhead | Negligible | Low (~1-2%) |
| Best for | Basic energy monitoring | Detailed profiling, research |

**Recommendation for Proyecto 10**:
- Use **hwmon** for basic energy measurements and when root is unavailable
- Use **AMD uProf** for:
  - Detailed per-core energy breakdown
  - Fine-grained power profiling (Zen3+)
  - When correlating energy with PMU events
  - Research requiring highest accuracy

**Installation (AMD uProf)**:
```bash
# Download from AMD Developer Central
wget https://developer.amd.com/wordpress/media/.../AMDuProf_Linux_x64_4.x.tar.bz2
tar xjf AMDuProf_Linux_x64_4.x.tar.bz2
sudo ./install.sh

# Enable MSR module (required for energy profiling)
sudo modprobe msr
# Make persistent
echo "msr" | sudo tee -a /etc/modules-load.d/msr.conf
```

**Alternative Methods**:
- `zenpower` kernel module (community alternative to `k10temp`, better for Ryzen)

### GPU Caveats

**NVIDIA**:
- Requires proprietary drivers; open-source `nouveau` has no power APIs
- `nvidia-smi` polling can introduce overhead (~1-2% on busy systems)
- Power readings are board-level (includes VRAM, not just GPU die)

**AMD**:
- ROCm support varies by GPU generation
- Consumer GPUs may have limited telemetry vs. datacenter Instinct series

**Intel**:
- Integrated GPUs share TDP budget with CPU; energy attribution is approximate
- Discrete Arc GPUs: experimental driver support, limited sysfs exposure

### NUMA Considerations

**Detection Limitations**:
- Requires `numactl` installed
- CPU affinity changes during execution can skew measurements
- Memory interleaving policies affect NUMA performance unpredictably

**Recommendations**:
- Pin processes to NUMA nodes for reproducibility
- Measure with `numastat` to verify local vs. remote memory access patterns

### Permissions

**Typical Restrictions (non-root users)**:
- RAPL: blocked by default (kernel >= 5.10 restricts via `perf_event_paranoid`)
- cpufreq writes: require `CAP_SYS_ADMIN`
- MSR access: requires `/dev/cpu/*/msr` read permissions
- hwmon: usually readable but some vendors restrict certain sensors

**Workarounds for HPC Clusters**:
- Ask admin to add udev rules: `SUBSYSTEM=="powercap", RUN+="/bin/chmod 0444 $env{DEVPATH}/energy_uj"`
- Use SLURM prologue scripts to relax permissions per-job
- Fallback to external power meters or IPMI if available

---

## Usage Examples

### Basic Execution

```bash
python detect_hardware_v2.py
```

Outputs human-readable report to stdout and saves `hardware_detect_report.json` in the script directory.

### Integrating with Experiment Metadata

```python
import json
from detect_hardware_v2 import HardwareDetectorV2

detector = HardwareDetectorV2()
hw_info = detector.info

# Merge with experiment metadata
experiment_metadata = {
    'experiment_id': 'exp_2025_10_23_001',
    'workload': 'gemm_small_N1024',
    'hardware': hw_info,
    'git_commit': 'abc123def',
    'timestamp': hw_info['timestamp']
}

with open('experiment_metadata.json', 'w') as f:
    json.dump(experiment_metadata, f, indent=2)
```

### Checking Capabilities Before Experiments

```python
from detect_hardware_v2 import HardwareDetectorV2

detector = HardwareDetectorV2()
caps = detector.info['capabilities']
cpu = detector.info['cpu']

# Check energy monitoring availability
if cpu['vendor'] == 'Intel':
    if not caps['rapl_readable']:
        print("WARNING: RAPL unavailable. Energy measurements will be missing.")
        # Fallback to timing-only experiments or external power meter
elif cpu['vendor'] == 'AMD':
    amd_energy = cpu.get('amd_energy', {})
    amd_uprof = cpu.get('amd_uprof', {})
    
    if amd_uprof.get('installed') and amd_uprof.get('msr_available'):
        print("AMD uProf available: using for detailed energy profiling")
        # Use AMD uProf for experiments
    elif amd_energy.get('readable'):
        print("Using hwmon for basic AMD energy monitoring")
        # Use hwmon fallback
    else:
        print("WARNING: No AMD energy monitoring available")

if not caps['tools']['perf']:
    print("WARNING: perf not installed. CPU profiling limited.")
```

### Using AMD uProf for Energy Measurements

```python
import subprocess
import json

def profile_with_uprof(workload_cmd, output_prefix):
    """Run workload with AMD uProf energy profiling"""
    uprof_cmd = [
        '/opt/AMDuProf_4.0-389/bin/AMDuProfCLI',
        'collect',
        '--event', 'power',
        '--event', 'energy',
        '--output-dir', output_prefix,
        '--',
    ] + workload_cmd
    
    subprocess.run(uprof_cmd, check=True)
    
    # Parse uProf output (CSV or text format)
    # Extract energy counters per core
    return parse_uprof_results(output_prefix)

# Example usage
energy_data = profile_with_uprof(['./gemm_benchmark', '1024'], 'exp_001')
```

---

## Recommendations for Cluster Administrators

### Enabling Read-Only RAPL Access

Add udev rule `/etc/udev/rules.d/99-rapl-readonly.rules`:

```
SUBSYSTEM=="powercap", ACTION=="add", RUN+="/bin/chmod 0444 $env{DEVPATH}/energy_uj"
```

Reload udev:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Installing Profiling Tools (CentOS 7)

```bash
# As admin
sudo yum install -y perf numactl cpupowerutils
sudo yum install -y kernel-tools  # provides turbostat
```

### AMD-Specific Setup

**For AMD systems, install AMD uProf for best energy profiling**:

1. Download from [AMD Developer Central](https://developer.amd.com/amd-uprof/)
2. Extract and install:
```bash
tar xjf AMDuProf_Linux_x64_*.tar.bz2
cd AMDuProf_Linux_x64_*/
sudo ./install.sh
```

3. Enable MSR module (required for energy counters):
```bash
sudo modprobe msr
sudo chmod 444 /dev/cpu/*/msr  # read-only access for all users
# Make persistent
echo "msr" | sudo tee -a /etc/modules-load.d/msr.conf
```

4. Verify:
```bash
/opt/AMDuProf_*/bin/AMDuProfCLI --version
ls -l /dev/cpu/0/msr  # should be readable
```

**Alternative: zenpower module (for better Ryzen support)**:
```bash
# On Fedora/RHEL-based
sudo dnf install dkms kernel-devel
git clone https://github.com/ocerman/zenpower.git
cd zenpower
make
sudo make install
sudo modprobe zenpower
```

### NVIDIA GPU Permissions

Allow non-root `nvidia-smi` queries (usually enabled by default):

```bash
# Verify
nvidia-smi -L  # should list GPUs without sudo
```

If restricted, check `/dev/nvidia*` permissions and NVIDIA Persistence Daemon configuration.

---

## Sample JSON Output

### Hypothetical CentOS 7 HPC Node

```json
{
  "schema_version": "2.0",
  "timestamp": "2025-10-23T18:00:00Z",
  "metadata": {
    "hostname": "hpc-node-042",
    "os": "Linux",
    "distribution": "CentOS Linux 7.9.2009",
    "kernel": "3.10.0-1160.el7.x86_64",
    "python_version": "2.7.5",
    "uname_full": "Linux hpc-node-042 3.10.0-1160.el7.x86_64 #1 SMP x86_64 GNU/Linux"
  },
  "system": {
    "arch": "x86_64"
  },
  "cpu": {
    "vendor": "Intel",
    "vendor_id": "GenuineIntel",
    "model": "Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz",
    "logical_cpus": 96,
    "sockets": 2,
    "cores_per_socket": 24,
    "threads_per_core": 2,
    "freq": {
      "driver": "intel_pstate",
      "available_governors": ["performance", "powersave"],
      "min_khz": 1000000,
      "max_khz": 4000000
    },
    "rapl": {
      "available": true,
      "readable": false,
      "domains": [
        "/sys/class/powercap/intel-rapl:0/energy_uj",
        "/sys/class/powercap/intel-rapl:1/energy_uj"
      ]
    },
    "amd_energy": {
      "available": false,
      "readable": false,
      "sensors": [],
      "driver": null
    },
    "amd_uprof": {
      "installed": false,
      "version": null,
      "path": null,
      "msr_available": false,
      "capabilities": []
    }
  },
  "numa": {
    "num_nodes": 2,
    "node_cpus": {
      "node_0": "0-23,48-71",
      "node_1": "24-47,72-95"
    }
  },
  "gpu": {
    "nvidia": [
      {
        "name": "Tesla V100-SXM2-32GB",
        "memory": "32480 MiB",
        "driver": "470.57.02",
        "minor": "0"
      },
      {
        "name": "Tesla V100-SXM2-32GB",
        "memory": "32480 MiB",
        "driver": "470.57.02",
        "minor": "1"
      }
    ],
    "amd": [],
    "intel": []
  },
  "hwmon": {
    "readable": true,
    "sensors": [
      {
        "device": "hwmon0",
        "name": "coretemp",
        "temps": ["temp1_input", "temp2_input"],
        "power": []
      }
    ]
  },
  "capabilities": {
    "tools": {
      "perf": true,
      "cpupower": true,
      "turbostat": false,
      "numactl": true,
      "nvidia-smi": true,
      "rocm-smi": false,
      "intel_gpu_top": false,
      "ipmitool": true
    },
    "permissions": {
      "is_root": false,
      "can_write_cpufreq": false
    },
    "rapl_readable": false,
    "amd_energy_readable": false,
    "hwmon_readable": true,
    "ipmitool": true
  },
  "warnings": [
    "RAPL not readable: Intel energy counters unavailable. Consider running as root or adjusting permissions.",
    "turbostat not found: useful for detailed CPU power/frequency monitoring."
  ]
}
```

---

## Changelog

### Version 2.0 (2025-10-23)
- **Enhanced AMD detection**: Full AMD uProf detection and capability reporting
- Added AMD energy sensor detection via hwmon (k10temp, zenpower)
- Added AMD uProf installation detection with version and path
- Added MSR availability check for AMD systems
- Added hwmon temperature/power sensor enumeration
- Added per-node NUMA CPU mapping
- Improved Intel GPU detection (min/max frequencies)
- Enhanced warnings/recommendations system with AMD-specific guidance
- Enhanced metadata with full uname output
- Schema version bump to 2.0

### Version 1.1 (Initial)
- Basic CPU, GPU, NUMA detection
- RAPL availability check
- Tool presence detection

---

## References

- [RAPL Interface Documentation](https://www.kernel.org/doc/html/latest/power/powercap/powercap.html)
- [Intel® 64 and IA-32 Architectures Software Developer's Manual](https://software.intel.com/content/www/us/en/develop/articles/intel-sdm.html)
- [Linux hwmon sysfs interface](https://www.kernel.org/doc/html/latest/hwmon/sysfs-interface.html)
- [NVIDIA Management Library (NVML) API](https://developer.nvidia.com/nvidia-management-library-nvml)
- [AMD ROCm Documentation](https://rocmdocs.amd.com/)
- [numactl man page](https://linux.die.net/man/8/numactl)

---

**Maintained by:** Proyecto 10 Team  
**Contact:** [Insert contact info]  
**License:** [Insert license]
