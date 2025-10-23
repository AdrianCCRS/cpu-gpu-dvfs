# AMD CPU Energy Profiling Guide — Proyecto 10

**Last Updated:** October 23, 2025  
**Target Systems:** AMD Zen2, Zen3, Zen4 (Ryzen, EPYC)

---

## Overview

This guide covers energy measurement and profiling strategies for AMD CPUs in the context of DVFS+ML experiments. AMD systems require different approaches than Intel due to architectural differences and tooling.

---

## Energy Measurement Methods for AMD

### Method Comparison

| Method | Availability | Granularity | Accuracy | Overhead | Requires Root |
|--------|-------------|-------------|----------|----------|---------------|
| **hwmon (k10temp)** | Built-in kernel | Package-level | Medium | Negligible | No (read-only) |
| **AMD uProf** | Manual install | Per-core/CCD | High | Low (~1%) | Yes (MSR access) |
| **zenpower** | Manual install | Package-level | Medium-High | Negligible | No (read-only) |
| **External meter** | Hardware | System-level | Highest | None | No |

---

## Method 1: hwmon (k10temp) — Basic Energy Monitoring

### Overview
- **Best for**: Quick experiments, CentOS 7 without sudo, basic energy accounting
- **Limitation**: Package-level energy only (no per-core breakdown)
- **Available on**: All Zen+ generations

### Detection
```bash
# Check for k10temp
ls /sys/class/hwmon/hwmon*/name | xargs grep -l k10temp

# Check for energy counter
find /sys/class/hwmon -name "energy*_input"
```

### Python Example
```python
import time

def read_package_energy():
    """Read AMD package energy from hwmon (microjoules)"""
    energy_file = '/sys/class/hwmon/hwmon0/energy1_input'  # adjust hwmon number
    with open(energy_file, 'r') as f:
        return int(f.read().strip())  # returns microjoules

# Measure energy for a workload
energy_start = read_package_energy()
time_start = time.time()

# Run your workload here
run_workload()

time_end = time.time()
energy_end = read_package_energy()

# Calculate consumed energy
energy_joules = (energy_end - energy_start) / 1e6
duration_s = time_end - time_start
average_power_watts = energy_joules / duration_s

print(f"Energy: {energy_joules:.2f} J")
print(f"Average Power: {average_power_watts:.2f} W")
print(f"Duration: {duration_s:.3f} s")
```

### Limitations
- **Counter wraparound**: Resets at ~4.2 million joules (~1h at 1000W)
- **Sampling latency**: Updates every ~1 second
- **No per-core data**: Only total package energy

---

## Method 2: AMD uProf — Advanced Profiling (RECOMMENDED)

### Overview
- **Best for**: Research, detailed per-core analysis, correlating energy with PMU events
- **Requires**: Manual installation, MSR access (root or capabilities)
- **Available on**: Zen2+ (best on Zen3+)

### Installation

#### Download and Install
```bash
# Download from AMD Developer Central
# https://developer.amd.com/amd-uprof/

# Extract
tar xjf AMDuProf_Linux_x64_4.0-389.tar.bz2
cd AMDuProf_Linux_x64_4.0-389/

# Install (requires sudo)
sudo ./install.sh
# Default install: /opt/AMDuProf_4.0-389/

# Add to PATH (optional)
echo 'export PATH=$PATH:/opt/AMDuProf_4.0-389/bin' >> ~/.bashrc
source ~/.bashrc
```

#### Enable MSR Access
```bash
# Load MSR kernel module
sudo modprobe msr

# Make persistent
echo "msr" | sudo tee -a /etc/modules-load.d/msr.conf

# Grant read access (for non-root users)
sudo chmod 444 /dev/cpu/*/msr

# Verify
ls -l /dev/cpu/0/msr
# Should show: cr--r--r-- (read-only for all)
```

### Usage Examples

#### Basic Energy Profiling
```bash
# Profile a command with energy collection
AMDuProfCLI collect \
  --event power \
  --event energy \
  --output-dir ./uprof_results \
  -- ./my_workload arg1 arg2

# Results in: uprof_results/Session-power-*.csv
```

#### CPU Frequency + Energy
```bash
# Collect frequency and energy simultaneously
AMDuProfCLI collect \
  --event energy \
  --event core-frequency \
  --interval 10 \
  --output-dir ./freq_energy_results \
  -- ./workload
```

#### Per-Core Energy (Zen3+)
```bash
# Detailed per-core breakdown
AMDuProfCLI collect \
  --event core-energy \
  --event package-energy \
  --output-dir ./per_core_results \
  -- ./workload
```

### Parsing uProf Output

```python
import pandas as pd
import glob

def parse_uprof_energy(output_dir):
    """Parse AMD uProf energy results"""
    csv_files = glob.glob(f"{output_dir}/Session-power-*.csv")
    
    if not csv_files:
        raise FileNotFoundError("No uProf results found")
    
    df = pd.read_csv(csv_files[0])
    
    # Extract total energy (check column names, varies by version)
    if 'Package Energy (J)' in df.columns:
        total_energy = df['Package Energy (J)'].sum()
    elif 'Energy (J)' in df.columns:
        total_energy = df['Energy (J)'].sum()
    else:
        # Fallback: parse from summary
        print("Warning: Energy column not found, check CSV manually")
        total_energy = None
    
    return {
        'total_energy_j': total_energy,
        'dataframe': df
    }

# Usage
results = parse_uprof_energy('./uprof_results')
print(f"Total Energy: {results['total_energy_j']:.2f} J")
```

### Integration with Proyecto 10

```python
import subprocess
import os

def run_experiment_with_uprof(kernel_name, freq_cpu, freq_gpu, input_size, run_id):
    """Run single experiment with AMD uProf profiling"""
    
    # Set CPU frequency (requires sudo or appropriate permissions)
    # See scripts/set_frequency.py
    
    output_dir = f"data/uprof_{kernel_name}_{run_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Build command
    workload_cmd = ['./benchmarks/cpu/dot', str(input_size)]
    uprof_cmd = [
        '/opt/AMDuProf_4.0-389/bin/AMDuProfCLI',
        'collect',
        '--event', 'power',
        '--event', 'energy',
        '--event', 'core-frequency',
        '--output-dir', output_dir,
        '--',
    ] + workload_cmd
    
    # Run with uProf
    result = subprocess.run(uprof_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"uProf error: {result.stderr}")
        return None
    
    # Parse results
    energy_data = parse_uprof_energy(output_dir)
    
    return {
        'kernel_name': kernel_name,
        'freq_cpu_mhz': freq_cpu,
        'input_size': input_size,
        'energy_j': energy_data['total_energy_j'],
        'run_id': run_id,
        'uprof_output': output_dir
    }
```

---

## Method 3: zenpower — Enhanced k10temp Alternative

### Overview
- **Best for**: Ryzen systems where k10temp is insufficient, no uProf available
- **Advantage**: Better sensor support than k10temp for consumer Ryzen
- **Limitation**: Still package-level only

### Installation (Fedora/CentOS)

```bash
# Install DKMS and kernel headers
sudo dnf install dkms kernel-devel

# Clone and build
git clone https://github.com/ocerman/zenpower.git
cd zenpower
make

# Install module
sudo make install
sudo modprobe zenpower

# Blacklist k10temp to avoid conflicts
echo "blacklist k10temp" | sudo tee /etc/modprobe.d/zenpower.conf

# Load on boot
echo "zenpower" | sudo tee /etc/modules-load.d/zenpower.conf

# Reboot or reload modules
sudo rmmod k10temp
sudo modprobe zenpower
```

### Usage
Same as k10temp (uses hwmon interface):
```python
# Detection
energy_file = '/sys/class/hwmon/hwmon?/energy1_input'  # find correct hwmon
# Read as before
```

---

## Choosing the Right Method

### Decision Tree

```
AMD System Detected
│
├─ Is AMD uProf installed?
│  ├─ Yes → Is MSR readable?
│  │  ├─ Yes → **Use AMD uProf** (best accuracy, per-core data)
│  │  └─ No  → Contact admin to enable MSR, fallback to hwmon
│  └─ No  → Can you install software?
│     ├─ Yes → **Install AMD uProf** (recommended for research)
│     └─ No  → Use hwmon (k10temp or zenpower)
│
└─ Fallback: External power meter or timing-only experiments
```

### Recommendations by System Type

| System | Recommended Method | Rationale |
|--------|-------------------|-----------|
| **EPYC (datacenter)** | AMD uProf | Best accuracy, per-CCD energy |
| **Ryzen (desktop/dev)** | AMD uProf or zenpower | uProf for research, zenpower for basic |
| **CentOS 7 (no sudo)** | hwmon (k10temp) | Built-in, no privileges needed |
| **Shared HPC cluster** | Coordinate with admin | uProf requires MSR access |

---

## Validation and Calibration

### Sanity Checks

```python
def validate_amd_energy_readings():
    """Basic validation for AMD energy counters"""
    
    # 1. Check for counter movement
    e1 = read_package_energy()
    time.sleep(1)
    e2 = read_package_energy()
    
    energy_delta = (e2 - e1) / 1e6  # Joules
    
    if energy_delta <= 0:
        print("ERROR: Energy counter not incrementing")
        return False
    
    # 2. Sanity check: idle power should be reasonable
    # EPYC idle: 50-100W, Ryzen idle: 20-50W
    idle_power = energy_delta / 1.0  # watts (1 second measurement)
    
    if idle_power < 10 or idle_power > 500:
        print(f"WARNING: Suspicious idle power: {idle_power:.1f} W")
        print("Check if counter is package-only or includes peripherals")
    
    print(f"Energy counter OK: {idle_power:.1f} W idle power")
    return True
```

### Comparing Methods

```python
import time

def compare_hwmon_vs_uprof(workload_func):
    """Compare hwmon and uProf measurements"""
    
    # Method 1: hwmon
    e_start = read_package_energy()
    t_start = time.time()
    workload_func()
    t_end = time.time()
    e_end = read_package_energy()
    
    hwmon_energy = (e_end - e_start) / 1e6
    hwmon_power = hwmon_energy / (t_end - t_start)
    
    print(f"hwmon: {hwmon_energy:.2f} J, {hwmon_power:.2f} W")
    
    # Method 2: AMD uProf (run separately)
    # Parse uProf output and compare
    # Expected: within 5-10% for package-level measurements
```

---

## Common Issues and Solutions

### Issue: MSR Not Readable
```
Error: Cannot access /dev/cpu/0/msr
```

**Solution:**
```bash
# Load MSR module
sudo modprobe msr

# Check permissions
ls -l /dev/cpu/0/msr

# If not readable, grant access
sudo chmod 444 /dev/cpu/*/msr
```

### Issue: Energy Counter Wraparound
```
Negative energy delta detected
```

**Solution:**
```python
def read_energy_safe(energy_file, max_value=4294967296):
    """Handle counter wraparound"""
    current = int(open(energy_file).read())
    
    # Detect wraparound (assuming previous value stored)
    if hasattr(read_energy_safe, 'prev') and current < read_energy_safe.prev:
        # Wrapped around
        delta = (max_value - read_energy_safe.prev) + current
    else:
        delta = current - getattr(read_energy_safe, 'prev', current)
    
    read_energy_safe.prev = current
    return delta
```

### Issue: uProf Command Not Found
```bash
# Add to PATH
export PATH=$PATH:/opt/AMDuProf_4.0-389/bin

# Or use full path
/opt/AMDuProf_4.0-389/bin/AMDuProfCLI --version
```

---

## Best Practices for Proyecto 10

1. **Always detect and document energy method used**:
   ```python
   detector = HardwareDetectorV2()
   energy_method = 'unknown'
   if detector.info['cpu']['amd_uprof']['installed']:
       energy_method = 'amd_uprof'
   elif detector.info['cpu']['amd_energy']['readable']:
       energy_method = 'hwmon'
   
   # Save to experiment metadata
   metadata['energy_measurement_method'] = energy_method
   ```

2. **Measure idle baseline**: Subtract idle power before analysis

3. **Multiple runs**: AMD energy can have higher variance than Intel RAPL
   - Recommend: 10+ runs per configuration

4. **Temperature awareness**: AMD chips throttle aggressively
   - Monitor temps via hwmon
   - Allow cooldown between runs

5. **Frequency validation**: Check actual vs. requested frequency
   ```bash
   cat /proc/cpuinfo | grep "cpu MHz"
   ```

---

## References

- [AMD uProf User Guide](https://developer.amd.com/amd-uprof/)
- [k10temp kernel documentation](https://www.kernel.org/doc/html/latest/hwmon/k10temp.html)
- [zenpower GitHub](https://github.com/ocerman/zenpower)
- [AMD MSR documentation](https://www.amd.com/system/files/TechDocs/24593.pdf)

---

**Maintained by:** Proyecto 10 Team  
**Last Updated:** October 23, 2025
