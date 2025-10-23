# Deployment Guide: Hardware Detector v2 to HPC Cluster

**Target Environment:** CentOS 7 HPC Cluster (no sudo access)  
**Script:** `detect_hardware_v2.py`  
**Date:** October 23, 2025

---

## Pre-Deployment Checklist

### Local Testing (Fedora/Development Machine)
- [x] Run smoke test: `python tests/test_detect_hardware.py --smoke`
- [x] Run full test suite: `python tests/test_detect_hardware.py --verbose`
- [x] Verify JSON output is valid
- [x] Check console report formatting

### Cluster Requirements
- [ ] SSH access to cluster login node
- [ ] Home directory with write permissions
- [ ] Python 2.7+ available (check with `python --version`)
- [ ] Network access for file transfer (scp/rsync)

---

## Deployment Steps

### Step 1: Prepare Files for Transfer

Create a deployment package:

```bash
cd /home/adrianccrs/Dev/CAGE/HPC/code

# Create deployment directory
mkdir -p deploy_hw_detector

# Copy essential files
cp scripts/detect_hardware_v2.py deploy_hw_detector/
cp docs/HARDWARE_DETECTOR_SPEC.md deploy_hw_detector/
cp docs/AMD_PROFILING_GUIDE.md deploy_hw_detector/
cp tests/test_detect_hardware.py deploy_hw_detector/

# Create README for cluster deployment
cat > deploy_hw_detector/README.txt << 'EOF'
Hardware Detector v2 - Deployment Package
==========================================

Files:
- detect_hardware_v2.py       Main detection script
- test_detect_hardware.py     Test suite
- HARDWARE_DETECTOR_SPEC.md   Technical documentation
- AMD_PROFILING_GUIDE.md      AMD-specific profiling guide

Quick Start:
1. python detect_hardware_v2.py
2. Check hardware_detect_report.json for results

Testing:
python test_detect_hardware.py --smoke

For full documentation, see HARDWARE_DETECTOR_SPEC.md
EOF

# Create tarball
tar czf hw_detector_v2_deploy.tar.gz deploy_hw_detector/
echo "Deployment package created: hw_detector_v2_deploy.tar.gz"
```

### Step 2: Transfer to Cluster

Replace `<username>` and `<cluster_hostname>` with your credentials:

```bash
# Option A: Using scp
scp hw_detector_v2_deploy.tar.gz <username>@<cluster_hostname>:~/

# Option B: Using rsync (preserves permissions)
rsync -avz hw_detector_v2_deploy.tar.gz <username>@<cluster_hostname>:~/

# Example:
# scp hw_detector_v2_deploy.tar.gz adrianccrs@hpc-cluster.university.edu:~/
```

### Step 3: Connect to Cluster

```bash
ssh <username>@<cluster_hostname>

# Example:
# ssh adrianccrs@hpc-cluster.university.edu
```

### Step 4: Extract and Verify on Cluster

```bash
# Extract deployment package
cd ~
tar xzf hw_detector_v2_deploy.tar.gz
cd deploy_hw_detector

# Verify Python version
python --version
# Should show Python 2.7.x or 3.x

# Make script executable
chmod +x detect_hardware_v2.py

# Run smoke test
python test_detect_hardware.py --smoke

# If smoke test passes, run full detection
python detect_hardware_v2.py
```

### Step 5: Review Output

```bash
# Check JSON output
cat hardware_detect_report.json | python -m json.tool | head -30

# Or use less for full output
less hardware_detect_report.json
```

### Step 6: Move to Project Directory

```bash
# Create scripts directory if needed
mkdir -p ~/proyecto10/scripts
mkdir -p ~/proyecto10/docs

# Copy files to project location
cp detect_hardware_v2.py ~/proyecto10/scripts/
cp test_detect_hardware.py ~/proyecto10/tests/
cp *.md ~/proyecto10/docs/

# Clean up deployment package
cd ~
rm -rf deploy_hw_detector hw_detector_v2_deploy.tar.gz
```

---

## Cluster-Specific Configuration

### For SLURM Clusters

Run detection as part of job submission:

```bash
#!/bin/bash
#SBATCH --job-name=hw_detect
#SBATCH --nodes=1
#SBATCH --time=00:05:00
#SBATCH --output=hw_detect_%j.out

# Load Python module if needed
# module load python/3.8

# Run detection
cd $HOME/proyecto10/scripts
python detect_hardware_v2.py

# Copy results with job ID
cp hardware_detect_report.json $HOME/proyecto10/data/hw_detect_node_${SLURM_NODEID}_job_${SLURM_JOB_ID}.json

echo "Hardware detection complete on node: $(hostname)"
```

Submit job:
```bash
sbatch detect_hardware_job.sh
```

### For PBS/Torque Clusters

```bash
#!/bin/bash
#PBS -N hw_detect
#PBS -l nodes=1:ppn=1
#PBS -l walltime=00:05:00

cd $PBS_O_WORKDIR
python detect_hardware_v2.py

# Copy with node name
cp hardware_detect_report.json $HOME/proyecto10/data/hw_detect_$(hostname)_${PBS_JOBID}.json
```

---

## Troubleshooting

### Issue: Python 2.7 Not Available

```bash
# Check for Python 3
python3 --version

# Use Python 3 if available
python3 detect_hardware_v2.py
```

### Issue: Permission Denied on /sys/class/powercap

**Expected behavior** - script will detect and report RAPL as "not readable":

```json
"rapl": {
  "available": true,
  "readable": false,
  "domains": [...]
}
```

This is normal for non-root users. The script handles this gracefully.

### Issue: "ImportError: No module named shutil"

This shouldn't happen on any standard Python installation. If it does:

```bash
# Check Python installation
python -c "import sys; print(sys.version)"

# Try with system Python
/usr/bin/python detect_hardware_v2.py
```

### Issue: Slow Execution

Some commands (like `numactl`, `nvidia-smi`) can be slow on some systems:

```bash
# Run with timing
time python detect_hardware_v2.py

# Expected: < 5 seconds on most systems
# If > 30 seconds, check which tool is slow:
# - Try running numactl --hardware manually
# - Try running nvidia-smi manually
```

---

## Validation on Cluster

### Quick Validation Script

Create `validate_hw_detection.sh`:

```bash
#!/bin/bash
# Validate hardware detection on cluster

echo "=== Hardware Detection Validation ==="
echo "Hostname: $(hostname)"
echo "Date: $(date)"
echo ""

# Run detection
python detect_hardware_v2.py > /dev/null

# Check JSON exists
if [ ! -f hardware_detect_report.json ]; then
    echo "ERROR: JSON report not created"
    exit 1
fi

# Validate JSON
python -c "import json; json.load(open('hardware_detect_report.json'))" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Invalid JSON"
    exit 1
fi

# Check schema version
VERSION=$(python -c "import json; print(json.load(open('hardware_detect_report.json'))['schema_version'])")
echo "Schema version: $VERSION"

# Check CPU vendor
VENDOR=$(python -c "import json; print(json.load(open('hardware_detect_report.json'))['cpu'].get('vendor', 'Unknown'))")
echo "CPU Vendor: $VENDOR"

# Check energy monitoring
if [ "$VENDOR" = "Intel" ]; then
    RAPL=$(python -c "import json; d=json.load(open('hardware_detect_report.json')); print(d['cpu']['rapl'].get('available', False))")
    echo "RAPL available: $RAPL"
elif [ "$VENDOR" = "AMD" ]; then
    AMD_ENERGY=$(python -c "import json; d=json.load(open('hardware_detect_report.json')); print(d['cpu']['amd_energy'].get('available', False))")
    echo "AMD Energy available: $AMD_ENERGY"
fi

echo ""
echo "✓ Validation passed"
```

Run validation:
```bash
chmod +x validate_hw_detection.sh
./validate_hw_detection.sh
```

---

## Integration with Proyecto 10 Workflow

### 1. Initial Cluster Characterization

Run once on each node type to characterize hardware:

```bash
# On login node
python detect_hardware_v2.py
mv hardware_detect_report.json ~/proyecto10/data/hw_login_node.json

# On compute node (via SLURM/PBS)
# Submit job to each partition/node type
```

### 2. Pre-Experiment Detection

Include in experiment scripts:

```python
#!/usr/bin/env python
# experiment_runner.py

from detect_hardware_v2 import HardwareDetectorV2
import json
import time

# Detect hardware
detector = HardwareDetectorV2()
hw_info = detector.info

# Create experiment metadata
experiment_metadata = {
    'experiment_id': 'exp_{}'.format(int(time.time())),
    'workload': 'gemm_N1024',
    'frequency_cpu': 2400,  # MHz
    'frequency_gpu': None,
    'hardware': hw_info,
    'timestamp': hw_info['timestamp']
}

# Save metadata
with open('experiment_metadata.json', 'w') as f:
    json.dump(experiment_metadata, f, indent=2)

# Run experiment
# ... your experiment code here ...
```

### 3. Batch Detection Across Nodes

```bash
#!/bin/bash
# detect_all_nodes.sh
# Run hardware detection on all available node types

for partition in standard highmem gpu; do
    echo "Detecting hardware in partition: $partition"
    sbatch --partition=$partition --job-name=hw_$partition detect_hardware_job.sh
done
```

---

## Expected Output Examples

### CentOS 7 Cluster Node (Intel Xeon)

```
--- Proyecto10 Hardware Detection (v2) ---
Host: hpc-node-042   Distro: CentOS Linux 7.9.2009   Kernel: 3.10.0-1160.el7.x86_64

CPU:
  Vendor: Intel  Model: Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz
  Logical CPUs: 96  Sockets: 2  Cores/socket: 24
  CPU freq range: 1.00 GHz - 4.00 GHz

Energy Monitoring:
  RAPL: available: True  readable: False

NUMA:
  numactl: installed
  nodes detected: 2

GPU:
  NVIDIA GPUs detected: 2
   - Tesla V100-SXM2-32GB  mem:32480 MiB driver:470.57.02

Capabilities:
  Tools present: perf, cpupower, numactl, nvidia-smi, ipmitool
  Tools missing: turbostat, rocm-smi, intel_gpu_top
  is_root: False
  can_write_cpufreq: False

WARNINGS & RECOMMENDATIONS:
  1. RAPL not readable: Intel energy counters unavailable. Consider running as root or adjusting permissions.
```

### AMD EPYC Node

```
--- Proyecto10 Hardware Detection (v2) ---
Host: amd-node-08   Distro: CentOS Linux 7.9.2009   Kernel: 3.10.0-1160.el7.x86_64

CPU:
  Vendor: AMD  Model: AMD EPYC 7763 64-Core Processor
  Logical CPUs: 128  Sockets: 1  Cores/socket: 64
  CPU freq range: 1.50 GHz - 3.50 GHz

Energy Monitoring:
  RAPL: available: False  readable: False
  AMD Energy (hwmon): available: True  readable: True
    driver: k10temp
  AMD uProf: not installed (recommended for advanced AMD profiling)

NUMA:
  numactl: installed
  nodes detected: 8

WARNINGS & RECOMMENDATIONS:
  1. AMD uProf not installed: highly recommended for advanced AMD CPU/energy profiling.
```

---

## Post-Deployment Checklist

- [ ] Script runs successfully on login node
- [ ] Script runs successfully on compute node (via job submission)
- [ ] JSON output is valid and complete
- [ ] Warnings are appropriate for the system
- [ ] Energy monitoring capabilities detected correctly
- [ ] Results saved to project data directory
- [ ] Documentation accessible to team

---

## Next Steps

1. **Collect baseline data**: Run detection on all node types
2. **Review warnings**: Address any critical capability gaps
3. **Configure energy monitoring**: Work with admin if RAPL/MSR access needed
4. **Integrate with experiments**: Add detection to experiment runner
5. **Document cluster specifics**: Create cluster-specific notes in `docs/`

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review `docs/HARDWARE_DETECTOR_SPEC.md`
3. For AMD systems, see `docs/AMD_PROFILING_GUIDE.md`
4. Contact cluster support for permission/access issues

---

**Document Version:** 1.0  
**Last Updated:** October 23, 2025  
**Maintained by:** Proyecto 10 Team
