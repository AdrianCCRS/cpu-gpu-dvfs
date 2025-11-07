# Energy Measurement Strategies - Proyecto 10

## Overview

Different cluster nodes have different CPU generations and capabilities for energy measurement. This document explains the fallback strategies implemented in `run_sweep.py`.

---

## Measurement Methods (Priority Order)

### 1. RAPL (Running Average Power Limit) ⭐ Best

**Requirements**:
- Intel CPU Sandy Bridge (2011) or newer
- Read access to `/sys/class/powercap/intel-rapl:0/energy_uj`

**Characteristics**:
- ✅ **Hardware counters**: Most accurate
- ✅ **High frequency**: Microsecond resolution
- ✅ **Low overhead**: Just read a sysfs file
- ✅ **Package + DRAM**: Separate domains available
- ⚠️ **Intel only**: Not available on AMD or old Intel CPUs

**How it works**:
```python
# Read counter before
energy_start = int(Path('/sys/class/powercap/intel-rapl:0/energy_uj').read_text())

# Run benchmark
time.sleep(5)

# Read counter after
energy_end = int(Path('/sys/class/powercap/intel-rapl:0/energy_uj').read_text())

# Calculate energy consumed (handle wraparound)
energy_uj = energy_end - energy_start
if energy_uj < 0:
    energy_uj += 2**32  # 32-bit counter wraparound
energy_J = energy_uj / 1e6
```

**Cluster nodes with RAPL**:
- ✅ guane04 (Xeon X7560 - Nehalem-EX, 2010) - **May not have RAPL**
- ✅ thor (Xeon E5-2609v3 - Haswell, 2014)
- ✅ felix (Xeon E7-8867v3 - Haswell-EX, 2015)

**Cluster nodes WITHOUT RAPL**:
- ❌ guane15 (Xeon E5645 - Westmere, 2010)
- ❌ yaje (if old architecture)

---

### 2. turbostat ⭐ Good Fallback

**Requirements**:
- Intel CPU (any generation with P-states/C-states)
- `turbostat` utility installed (part of linux-tools)
- Root/sudo access

**Characteristics**:
- ✅ **Works on old CPUs**: Westmere (2010), Nehalem (2008)
- ✅ **Per-package power**: Estimates from MSRs
- ⚠️ **Requires root**: Needs MSR access
- ⚠️ **Higher overhead**: Spawns external process
- ⚠️ **Estimates only**: Not as accurate as RAPL

**How it works**:
```bash
# Run turbostat for brief interval
sudo turbostat --quiet --show PkgWatt --interval 1 sleep 0.5
# Output:
# PkgWatt
# 45.67
```

```python
def _read_turbostat_power() -> Optional[float]:
    result = subprocess.run(
        ['sudo', 'turbostat', '--quiet', '--show', 'PkgWatt', 
         '--interval', '1', 'sleep', '0.5'],
        capture_output=True, text=True, timeout=3
    )
    lines = result.stdout.strip().split('\n')
    return float(lines[-1])  # Power in watts

# Energy calculation
power_start = _read_turbostat_power()  # W
# Run benchmark
time_elapsed = 5.0  # seconds
power_end = _read_turbostat_power()    # W

avg_power = (power_start + power_end) / 2.0
energy_J = avg_power * time_elapsed
```

**Advantages for guane15**:
- ✅ Xeon E5645 (Westmere) supports turbostat
- ✅ Can measure package power even without RAPL
- ✅ Better than nothing!

**Limitations**:
- Each read takes ~0.5-1 second (slow)
- Sudo required for every measurement
- Power readings are estimates, not precise counters

---

### 3. hwmon (Hardware Monitoring) ⚠️ Basic

**Requirements**:
- AMD CPU with `amd_energy` driver (kernel 5.8+)
- Or Intel CPU with `coretemp` + power sensors
- Read access to `/sys/class/hwmon/hwmon*/`

**Characteristics**:
- ✅ **Works on AMD**: Main method for Ryzen/EPYC
- ✅ **Socket-level**: Basic energy counters
- ⚠️ **Limited availability**: Rare on Intel, needs modern AMD
- ⚠️ **Coarse granularity**: Usually updates at ~1 Hz

**How it works**:
```python
# Find hwmon device with energy sensor
for hwmon_dev in Path('/sys/class/hwmon').iterdir():
    name = (hwmon_dev / 'name').read_text().strip()
    if name in ['amd_energy', 'k10temp', 'zenpower']:
        # Found AMD energy sensor
        energy_file = hwmon_dev / 'energy1_input'
        energy_uj = int(energy_file.read_text())
        break

# Same counter-based approach as RAPL
energy_start = read_hwmon_energy()
# Run benchmark
energy_end = read_hwmon_energy()
energy_J = (energy_end - energy_start) / 1e6
```

**Cluster nodes with hwmon energy**:
- ❓ guane15: Has `coretemp` hwmon but **no energy sensors** (temperature only)
- ✅ Future AMD nodes: Would work automatically

---

### 4. No Measurement ❌ Fallback of Last Resort

**When used**:
- Old CPUs without RAPL or turbostat support
- No sudo access for turbostat
- No hwmon energy sensors

**Characteristics**:
- ❌ **No energy data**: `energy_J_cpu = None` in CSV
- ✅ **Time still measured**: Can train time-only models
- ✅ **Other metrics available**: IPC, cache misses, etc.

**Impact on dataset**:
```csv
run_id,time_s,energy_J_cpu,energy_J_gpu,edp_Js,ipc,cache_misses
run_001,2.345,NULL,NULL,NULL,1.23,45678
```

**ML model implications**:
- Can't predict EDP (Energy-Delay Product)
- Can still predict execution time
- Can use time as proxy for energy in some cases

---

## Implementation in run_sweep.py

### Auto-Detection Logic

```python
def _detect_energy_method(self) -> str:
    # Try RAPL first (best)
    rapl_path = Path('/sys/class/powercap/intel-rapl:0/energy_uj')
    if rapl_path.is_file() and os.access(rapl_path, os.R_OK):
        return 'rapl'
    
    # Try turbostat second (good fallback)
    if which('turbostat'):
        try:
            result = subprocess.run(
                ['sudo', 'turbostat', '--quiet', '--show', 'PkgWatt', 
                 '--interval', '1', 'sleep', '0.1'],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0:
                return 'turbostat'
        except:
            pass
    
    # Try hwmon third (AMD or some Intel)
    for hwmon in Path('/sys/class/hwmon').iterdir():
        name = (hwmon / 'name').read_text().strip()
        if name in ['amd_energy', 'k10temp', 'zenpower']:
            for energy_file in hwmon.glob('energy*_input'):
                if os.access(energy_file, os.R_OK):
                    return 'hwmon'
    
    # No method available
    return 'none'
```

### Unified Interface

```python
def read_cpu_energy(self) -> Optional[float]:
    """Read energy using best available method"""
    if self.energy_method == 'rapl':
        return self._read_rapl_energy()      # Returns µJ (counter)
    elif self.energy_method == 'turbostat':
        return self._read_turbostat_power()  # Returns W (instantaneous)
    elif self.energy_method == 'hwmon':
        return self._read_hwmon_energy()     # Returns µJ (counter)
    else:
        return None

def _calculate_cpu_energy(self, start, end, time_s):
    """Convert method-specific readings to joules"""
    if self.energy_method in ['rapl', 'hwmon']:
        # Counter-based: end - start (with wraparound)
        energy_uj = end - start
        if energy_uj < 0:
            energy_uj += 2**32
        return energy_uj / 1e6
    
    elif self.energy_method == 'turbostat':
        # Power-based: average power × time
        avg_power = (start + end) / 2.0
        return avg_power * time_s
    
    return None
```

---

## Cluster Node Recommendations

### guane15 (Xeon E5645 - Westmere, 2010)

**Best strategy**: Use **turbostat**

```bash
# Test if turbostat works
sudo turbostat --quiet --show PkgWatt --interval 1 sleep 1

# If successful, run sweep with sudo privileges
sudo python3 scripts/run_sweep.py -c configs/sweep_config.json
```

**Expected output during sweep**:
```
=== Checking System Capabilities ===
Hostname: guane15.uis.edu.co
CPU: Intel(R) Xeon(R) CPU E5645 @ 2.40GHz
GPU: Tesla M2075
perf: available
nvidia-smi: available
turbostat: available
CPU Energy Method: ✓ turbostat (good - kernel estimates)
```

**Alternative**: Run without energy measurement
```bash
# Will collect time, IPC, cache metrics but no energy
python3 scripts/run_sweep.py -c configs/sweep_config.json
```

**CSV output**:
```csv
timestamp,run_id,hostname,cpu_model,time_s,energy_J_cpu,ipc,cache_misses
2025-11-07T...,run_000001,guane15,Xeon E5645,2.456,45.67,1.23,45678
```

---

### thor/felix (Haswell, 2014-2015)

**Best strategy**: Use **RAPL** (should be available)

```bash
# Verify RAPL is readable
cat /sys/class/powercap/intel-rapl:0/energy_uj

# If not readable, fix permissions
sudo chmod -R a+r /sys/class/powercap/intel-rapl/

# Run sweep
python3 scripts/run_sweep.py -c configs/sweep_config.json
```

**Expected output**:
```
CPU Energy Method: ✓ RAPL (best - hardware counters)
```

---

### guane04 (Xeon X7560 - Nehalem-EX, 2010)

**Uncertain**: Nehalem-EX may or may not have RAPL support.

**Test procedure**:
```bash
# Check for RAPL
ls /sys/class/powercap/intel-rapl*/energy_uj

# If not found, use turbostat
sudo turbostat --quiet --show PkgWatt sleep 1
```

---

## GPU Energy Measurement

**Current status**: Placeholder in code (all nodes)

```python
metrics['energy_J_gpu'] = None  # TODO: integrate NVML
```

**Future implementation**: Use NVML (pynvml)
```python
import pynvml

pynvml.nvmlInit()
handle = pynvml.nvmlDeviceGetHandleByIndex(0)

# Sample power over benchmark duration
power_samples = []
while benchmark_running:
    power_mW = pynvml.nvmlDeviceGetPowerUsage(handle)
    power_samples.append(power_mW / 1000.0)  # Convert to W
    time.sleep(0.1)

avg_power = sum(power_samples) / len(power_samples)
energy_J = avg_power * total_time
```

**Available on**:
- ✅ All cluster nodes (Tesla M2050, M2075, K20c, GTX TITAN X)
- Requires `nvidia-ml-py` package: `pip install nvidia-ml-py`

---

## Troubleshooting

### Problem: "turbostat: no /dev/cpu/0/msr"

**Solution**: Load MSR kernel module
```bash
sudo modprobe msr
ls /dev/cpu/0/msr  # Should exist now
```

### Problem: "Permission denied" on RAPL

**Solution**: Fix permissions (temporary)
```bash
sudo chmod -R a+r /sys/class/powercap/intel-rapl/
```

**Solution**: Fix permissions (persistent)
```bash
# Create udev rule
sudo tee /etc/udev/rules.d/99-rapl.rules << EOF
SUBSYSTEM=="powercap", KERNEL=="intel-rapl:*", RUN+="/bin/chmod -R a+r /sys/class/powercap/intel-rapl"
EOF

sudo udevadm control --reload-rules
```

### Problem: turbostat needs root but no sudo access

**Solution 1**: Ask admin to grant sudo access for turbostat
```bash
# Add to /etc/sudoers.d/turbostat
username ALL=(ALL) NOPASSWD: /usr/bin/turbostat
```

**Solution 2**: Run entire sweep with sudo
```bash
sudo python3 scripts/run_sweep.py -c config.json
```

**Solution 3**: Collect dataset without energy
```bash
# Still useful - can train time prediction models
python3 scripts/run_sweep.py -c config.json
```

---

## Summary Table

| Node | CPU | RAPL | turbostat | hwmon | Recommendation |
|------|-----|------|-----------|-------|----------------|
| guane15 | E5645 (2010) | ❌ | ✅ | ❌ | Use turbostat |
| guane04 | X7560 (2010) | ❓ | ✅ | ❌ | Test RAPL, fallback to turbostat |
| thor | E5-2609v3 (2014) | ✅ | ✅ | ❌ | Use RAPL |
| felix | E7-8867v3 (2015) | ✅ | ✅ | ❌ | Use RAPL |
| yaje | ? | ❓ | ❓ | ❌ | Run detect_hardware.py first |

---

**Last Updated**: 2025-11-07  
**Script Version**: run_sweep.py with multi-method energy support
