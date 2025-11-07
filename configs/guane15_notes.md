# Configuration Notes for guane15

## Hardware Summary
- **CPU**: Intel Xeon E5645 (Westmere, 2010)
- **Frequency Range**: 1.6 - 2.4 GHz (1600-2400 MHz)
- **DVFS Driver**: `pcc-cpufreq` (Processor Clocking Control)
- **Governors**: conservative, userspace, powersave, ondemand, performance
- **GPUs**: 8× Tesla M2075
- **Energy Measurement**: No RAPL (use turbostat with sudo)

---

## Important: pcc-cpufreq Driver Limitations

### What is pcc-cpufreq?

`pcc-cpufreq` (Processor Clocking Control) is a **platform-specific** frequency scaling driver used on:
- HP ProLiant servers
- Some Dell PowerEdge servers
- Other enterprise systems with ACPI-based frequency control

**Key difference from acpi-cpufreq**:
- Uses platform firmware (BIOS) for frequency transitions
- May not support arbitrary frequency selection
- Often works better with **governor-based** control than direct frequency setting

### Frequency Control Strategy

**Option 1: Governor-based (RECOMMENDED for pcc-cpufreq)**

Instead of setting exact frequencies, use governors:

```bash
# Set governor to "performance" (max frequency)
sudo cpupower frequency-set -g performance

# Set governor to "powersave" (min frequency)
sudo cpupower frequency-set -g powersave

# Set governor to "userspace" (allows manual control)
sudo cpupower frequency-set -g userspace
# Then try to set frequency
sudo cpupower frequency-set -f 2000MHz
```

**Option 2: Direct frequency (may not work)**

```bash
# This MAY fail with pcc-cpufreq
sudo cpupower frequency-set -g userspace
sudo cpupower frequency-set -f 2000MHz

# Check if it actually changed
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
```

### Testing Frequency Control

Before running the full sweep, test if frequency control works:

```bash
# 1. Check current driver
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver
# Expected: pcc-cpufreq

# 2. Try setting to userspace
sudo cpupower frequency-set -g userspace

# 3. Try setting a frequency
sudo cpupower frequency-set -f 1600MHz
sleep 1
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq

# 4. Try another frequency
sudo cpupower frequency-set -f 2400MHz
sleep 1
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq

# If the frequency changes, direct control works!
# If it stays the same, pcc-cpufreq is ignoring our requests.
```

### Workaround if Direct Frequency Fails

If `pcc-cpufreq` ignores frequency setting commands, modify `run_sweep.py` to use governor switching:

```python
# Instead of:
cpu_frequencies = [1600, 1800, 2000, 2200, 2400]

# Use governors as "frequency levels":
cpu_configs = [
    {'governor': 'powersave'},     # Min frequency (1600 MHz)
    {'governor': 'ondemand'},      # Dynamic (varies)
    {'governor': 'performance'},   # Max frequency (2400 MHz)
]
```

This gives you 3 configurations instead of 5, but they're guaranteed to work.

---

## Recommended Sweep Configuration

### Conservative Approach (3 CPU states × 6 GPU × 4 benchmarks × 5 sizes × 5 reps = 1800 experiments)

```json
{
  "description": "Governor-based sweep for guane15 (pcc-cpufreq)",
  "cpu_configs": [
    {
      "name": "min_freq",
      "governor": "powersave",
      "expected_mhz": 1600
    },
    {
      "name": "balanced",
      "governor": "ondemand",
      "expected_mhz": "dynamic"
    },
    {
      "name": "max_freq",
      "governor": "performance",
      "expected_mhz": 2400
    }
  ],
  "gpu_frequencies": [500, 700, 900, 1100, 1300, 1500],
  "benchmarks": [...],
  "repetitions": 5
}
```

### Optimistic Approach (5 CPU freqs - if direct control works)

```json
{
  "description": "Direct frequency sweep for guane15 (if pcc-cpufreq allows)",
  "cpu_frequencies": [1600, 1800, 2000, 2200, 2400],
  "gpu_frequencies": [500, 700, 900, 1100, 1300, 1500],
  "benchmarks": [...],
  "repetitions": 5
}
```

**Use this only after confirming direct frequency control works!**

---

## Energy Measurement Setup

Since guane15 lacks RAPL, use turbostat:

### Grant sudo access to turbostat (recommended)

```bash
# Ask admin to add this to /etc/sudoers.d/turbostat
yacacerest ALL=(ALL) NOPASSWD: /usr/bin/turbostat
```

### Test turbostat

```bash
# Test if turbostat works
sudo turbostat --quiet --show PkgWatt --interval 1 sleep 1

# Expected output:
# PkgWatt
# 45.67
```

### Run sweep with sudo

```bash
# If sudoers configured for turbostat only
python3 scripts/run_sweep.py -c configs/sweep_config_example.json

# If full sudo needed
sudo -E python3 scripts/run_sweep.py -c configs/sweep_config_example.json
```

---

## Alternative: Skip Energy Measurement

If sudo is not available, run without energy:

```bash
python3 scripts/run_sweep.py -c configs/sweep_config_example.json
```

**Collected metrics**:
- ✅ Time (execution time)
- ✅ IPC (instructions per cycle)
- ✅ Cache misses
- ✅ All perf counters
- ❌ CPU energy (will be NULL)
- ❌ EDP (will be NULL)

**You can still**:
- Train time prediction models
- Analyze IPC vs frequency relationship
- Study cache behavior
- Later: interpolate energy from other nodes with RAPL

---

## GPU Frequency Control

Tesla M2075 (Fermi GF110, 2011) frequency characteristics:

**Specifications**:
- **Base Clock**: 575 MHz
- **Boost**: Not supported (pre-Kepler architecture)
- **Memory Clock**: 1566 MHz (3.0 Gbps GDDR5)
- **Compute Capability**: 2.0
- **TDP**: 225W

**Important**: Tesla M2075 has **limited frequency control** compared to modern GPUs.

### Check Supported Frequencies

**CRITICAL**: Before running the sweep, verify what frequencies are actually supported:

```bash
# Query all supported frequency combinations
nvidia-smi -i 0 -q -d SUPPORTED_CLOCKS

# Expected output format:
#   Supported Clocks
#     Memory                          : 1566 MHz
#       Graphics                      : 700 MHz
#       Graphics                      : 625 MHz
#       Graphics                      : 550 MHz
#       Graphics                      : 475 MHz
#       Graphics                      : 405 MHz
```

**Common issue**: Old driver version (390.116) may have limited frequency options.

### Setting GPU Frequency

```bash
# Enable persistence mode (REQUIRED)
sudo nvidia-smi -i 0 -pm 1

# Lock GPU 0 to specific frequency
sudo nvidia-smi -i 0 -lgc 550

# Verify the change
nvidia-smi --query-gpu=clocks.gr,clocks.sm --format=csv -i 0

# Expected output:
# clocks.graphics [MHz], clocks.sm [MHz]
# 550 MHz, 550 MHz
```

### Frequency Locking Limitations

**Problem**: `-lgc` (Lock Graphics Clock) may not work on old Tesla cards with old drivers.

**Alternative methods**:

1. **Application clocks** (preferred for Tesla):
```bash
# List available application clocks
nvidia-smi -i 0 -q -d SUPPORTED_CLOCKS

# Set application clocks (memory, graphics)
sudo nvidia-smi -i 0 -ac 1566,550

# This sets:
# - Memory clock: 1566 MHz
# - Graphics clock: 550 MHz
```

2. **Reset to default**:
```bash
# Reset all clock settings
sudo nvidia-smi -i 0 -rac

# Disable persistence mode when done
sudo nvidia-smi -i 0 -pm 0
```

### Recommended GPU Frequencies for Sweep

Based on Tesla M2075 typical frequency steps:

```json
{
  "gpu_frequencies": [405, 475, 550, 625, 700]
}
```

**Rationale**:
- **405 MHz**: Minimum supported (power saving)
- **475 MHz**: Low power mode
- **550 MHz**: Mid-range balanced
- **625 MHz**: Performance mode
- **700 MHz**: Maximum (may approach or exceed base clock)

**Note**: If these frequencies don't work, query supported clocks and adjust accordingly.

### Testing GPU Frequency Control

Before running the full sweep, test on one GPU:

```bash
# Test script
#!/bin/bash
set -x

# Enable persistence mode
sudo nvidia-smi -pm 1

# Test each frequency
for freq in 405 475 550 625 700; do
    echo "Testing ${freq} MHz..."
    
    # Method 1: Try -lgc
    sudo nvidia-smi -i 0 -lgc $freq
    sleep 2
    
    # Check actual frequency
    nvidia-smi --query-gpu=clocks.gr --format=csv,noheader,nounits -i 0
    
    echo "---"
done

# Reset
sudo nvidia-smi -rac
```

**Expected behavior**:
- ✅ Frequency changes to requested value
- ⚠️ Frequency changes to nearest supported value
- ❌ Frequency doesn't change (method not supported)

### Fallback: Fixed Application Clocks

If dynamic frequency locking doesn't work, use a **2-point sweep**:

```json
{
  "gpu_configs": [
    {
      "name": "low_power",
      "memory_mhz": 1566,
      "graphics_mhz": 405,
      "method": "application_clocks"
    },
    {
      "name": "max_performance", 
      "memory_mhz": 1566,
      "graphics_mhz": 700,
      "method": "application_clocks"
    }
  ]
}
```

This reduces experiments: **5 CPU × 2 GPU × 4 benchmarks × 5 sizes × 5 reps = 1000 experiments**

---

## GPU Energy Measurement

### NVML Power Monitoring

Tesla M2075 supports power monitoring via NVML:

```bash
# Check if power monitoring is available
nvidia-smi --query-gpu=power.draw,power.limit --format=csv -i 0

# Expected output:
# power.draw [W], power.limit [W]
# 95.50 W, 225.00 W
```

**Sampling method** (since no direct energy counter):

```python
import pynvml
import time

pynvml.nvmlInit()
handle = pynvml.nvmlDeviceGetHandleByIndex(0)

# Sample power every 100ms during benchmark
power_samples = []
start_time = time.time()

while benchmark_running:
    power_mW = pynvml.nvmlDeviceGetPowerUsage(handle)  # milliwatts
    power_samples.append(power_mW / 1000.0)  # Convert to watts
    time.sleep(0.1)  # 100ms sampling

elapsed_time = time.time() - start_time

# Calculate energy (trapezoidal integration)
avg_power = sum(power_samples) / len(power_samples)
energy_J = avg_power * elapsed_time
```

**Accuracy**: ±5% (limited by sampling rate)

### Alternative: nvidia-smi polling

If NVML integration is complex:

```bash
# Run nvidia-smi in background during benchmark
nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits -i 0 -l 1 > power_log.txt &
NVIDIA_PID=$!

# Run benchmark
./benchmark

# Stop nvidia-smi
kill $NVIDIA_PID

# Calculate average power
awk '{sum+=$1; count++} END {print sum/count}' power_log.txt
```

---

## Multiple GPU Considerations

---

## Multiple GPU Considerations

guane15 has **8 Tesla M2075 GPUs**. Decisions needed:

### Option 1: Use One GPU (RECOMMENDED for initial sweep)

**Simplest approach**:
```json
{
  "gpu_id": 0,
  "gpu_frequencies": [405, 475, 550, 625, 700]
}
```

**Advantages**:
- ✅ Faster sweep (one GPU only)
- ✅ Consistent results
- ✅ Easier to debug
- ✅ Other 7 GPUs available for other users

**Implementation**: Set `CUDA_VISIBLE_DEVICES=0` in environment

### Option 2: Multi-GPU Benchmarks

**For distributed/multi-GPU workloads**:
```bash
# Set all 8 GPUs to same frequency
for i in {0..7}; do
    sudo nvidia-smi -i $i -pm 1
    sudo nvidia-smi -i $i -lgc 550
done

# Run multi-GPU benchmark
mpirun -np 8 ./benchmark
```

**Sweep complexity**: Each GPU can have different frequency → combinatorial explosion

### Option 3: Sweep Across GPUs (for heterogeneity study)

**Advanced**: Compare GPU-to-GPU variation
```bash
# Same frequency on all GPUs, but collect metrics per GPU
# Useful to study manufacturing variations
```

**Recommendation**: Start with **Option 1** (single GPU, GPU 0)

---

## Troubleshooting

### Problem: "pcc-cpufreq: frequency transition failed"

**Cause**: Platform firmware (BIOS) doesn't support that frequency

**Solution**: Use governor-based approach or check BIOS settings for frequency control

### Problem: Frequency doesn't change

```bash
# Check if frequency actually changed
watch -n 0.5 'cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq | head -4'

# Compare to setspeed
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_setspeed
```

**If they don't match**: pcc-cpufreq is not honoring requests. Use governor approach.

### Problem: turbostat returns 0.00 watts

**Cause**: MSR (Model-Specific Register) access blocked

**Solution**:
```bash
# Load MSR module
sudo modprobe msr

# Verify
ls /dev/cpu/0/msr
```

---

### Problem: "Setting applications clocks is not supported for GPU ..."

**Cause**: Old driver or unsupported feature on this specific card

**Solution**: Verify driver version and GPU support
```bash
nvidia-smi --query-gpu=driver_version,vbios_version --format=csv

# Driver 390.116 is quite old (2018)
# Consider updating to newer driver if possible
# Tesla M2075 officially supported up to driver 418.x
```

### Problem: GPU frequency doesn't change

```bash
# Check actual clocks
watch -n 0.5 'nvidia-smi --query-gpu=clocks.gr,clocks.sm,clocks.mem --format=csv -i 0'

# Check if persistence mode is enabled
nvidia-smi --query-gpu=persistence_mode --format=csv -i 0
```

### Problem: "N/A" for supported clocks

**Cause**: Feature not available in driver or GPU

**Workaround**: Use **2-state approach** (min/max only)
```bash
# Set to lowest P-state (power state)
sudo nvidia-smi -i 0 -pm 1
sudo nvidia-smi -i 0 -ac 1566,405

# Set to highest P-state
sudo nvidia-smi -i 0 -ac 1566,700
```

---

## Summary for guane15

### Hardware
- **CPU**: 2× Xeon E5645 (12 cores, 24 threads, 1.6-2.4 GHz)
- **GPU**: 8× Tesla M2075 (6 GB GDDR5 each, ~405-700 MHz)
- **Memory**: ~104 GB RAM (NUMA)
- **Driver**: NVIDIA 390.116 (old but stable)

### Recommended Configuration

**Conservative (guaranteed to work)**:
- CPU: 3 governors (powersave, ondemand, performance)
- GPU: 2 frequencies (405, 700 MHz)
- Total: **3 × 2 × 4 × 5 × 5 = 600 experiments** (~2-3 hours)

**Optimistic (if frequency control works)**:
- CPU: 5 frequencies (1600, 1800, 2000, 2200, 2400 MHz)
- GPU: 5 frequencies (405, 475, 550, 625, 700 MHz)
- Total: **5 × 5 × 4 × 5 × 5 = 2500 experiments** (~8-12 hours)

### Pre-Flight Checklist

Before running the full sweep:

- [ ] Test CPU frequency control (pcc-cpufreq)
- [ ] Query GPU supported clocks (`nvidia-smi -q -d SUPPORTED_CLOCKS`)
- [ ] Test GPU frequency locking on one GPU
- [ ] Verify turbostat works (`sudo turbostat --quiet sleep 1`)
- [ ] Check sudo permissions for cpupower, nvidia-smi, turbostat
- [ ] Compile/test all 4 benchmarks
- [ ] Do a **mini sweep** first (2 CPU × 2 GPU × 1 benchmark × 1 size × 2 reps = 8 runs)

### Mini Sweep Test

```json
{
  "description": "Test configuration - verify everything works",
  "cpu_frequencies": [1600, 2400],
  "gpu_frequencies": [405, 700],
  "benchmarks": [
    {
      "name": "dot_product",
      "cmd": "./benchmarks/cpu/dot {input_size}"
    }
  ],
  "input_sizes": [1000000],
  "repetitions": 2,
  "output_file": "data/test_sweep.csv"
}
```

Run this first! If it works, proceed to full sweep. If it fails, debug before wasting 12 hours.

Good luck! 🚀
