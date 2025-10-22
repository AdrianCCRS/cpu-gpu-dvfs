#!/bin/bash
# Hardware Detection Script for Proyecto 10
# Detects CPU, GPU, and available frequency scaling capabilities

set -e

echo "================================"
echo "  Hardware Detection - Proyecto 10"
echo "================================"
echo ""

# System info
echo "## System Information"
echo "Hostname: $(hostname)"
echo "Kernel: $(uname -r)"
echo "Date: $(date -I)"
echo ""

# CPU Information
echo "## CPU Information"
lscpu | grep -E "Model name|CPU\(s\)|Thread|Core|Socket|MHz"
echo ""

# CPU Frequency Scaling
echo "## CPU Frequency Scaling"
if [ -d "/sys/devices/system/cpu/cpu0/cpufreq" ]; then
    echo "✓ CPUFreq interface available"
    echo "Available governors:"
    cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors 2>/dev/null || echo "  (unable to read)"
    echo "Available frequencies:"
    cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_frequencies 2>/dev/null || echo "  (unable to read)"
    echo "Current governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo 'unknown')"
else
    echo "✗ CPUFreq interface not found"
fi
echo ""

# RAPL Support
echo "## RAPL (Running Average Power Limit)"
if [ -d "/sys/class/powercap/intel-rapl" ]; then
    echo "✓ RAPL interface available"
    ls /sys/class/powercap/intel-rapl/ | grep "intel-rapl:" || true
else
    echo "✗ RAPL interface not found"
fi

# Check MSR module
if lsmod | grep -q msr; then
    echo "✓ MSR module loaded"
else
    echo "⚠ MSR module not loaded (try: sudo modprobe msr)"
fi
echo ""

# GPU Information - NVIDIA
echo "## NVIDIA GPU"
if command -v nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA driver installed"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    echo ""
    echo "Supported clocks:"
    nvidia-smi -q -d SUPPORTED_CLOCKS | head -20 || echo "  (unable to query)"
else
    echo "✗ nvidia-smi not found"
fi
echo ""

# GPU Information - Intel
echo "## Intel GPU"
if command -v intel_gpu_top &> /dev/null; then
    echo "✓ intel_gpu_top available"
else
    echo "✗ intel_gpu_top not found (install: apt-get install intel-gpu-tools)"
fi

if [ -d "/sys/class/drm/card0" ]; then
    echo "✓ DRM interface found"
    ls /sys/class/drm/ | grep "card[0-9]"
else
    echo "⚠ DRM interface not found"
fi
echo ""

# Perf support
echo "## Performance Counters"
if command -v perf &> /dev/null; then
    echo "✓ perf tool available"
    perf list | grep -E "cycles|instructions|cache" | head -5 || true
else
    echo "✗ perf not found (install: apt-get install linux-tools-generic)"
fi
echo ""

# Check permissions
echo "## Permission Check"
echo -n "CPU frequency control: "
if [ -w "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor" ]; then
    echo "✓ writable"
else
    echo "✗ requires root/sudo"
fi

echo -n "RAPL read access: "
if [ -r "/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj" ] 2>/dev/null; then
    echo "✓ readable"
else
    echo "✗ requires root/sudo or permissions adjustment"
fi

echo ""
echo "================================"
echo "Detection complete. Save this output to docs/hardware_specs.md"
