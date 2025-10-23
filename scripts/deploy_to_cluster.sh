#!/bin/bash
# deploy_to_cluster.sh
# Quick deployment script for hardware detector to HPC cluster
# Usage: ./deploy_to_cluster.sh <username> <cluster_hostname>

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -lt 2 ]; then
    echo -e "${RED}Error: Missing arguments${NC}"
    echo "Usage: $0 <username> <cluster_hostname>"
    echo "Example: $0 adrianccrs hpc-cluster.university.edu"
    exit 1
fi

USERNAME=$1
CLUSTER=$2

echo -e "${GREEN}=== Hardware Detector v2 - Cluster Deployment ===${NC}"
echo "Target: ${USERNAME}@${CLUSTER}"
echo ""

# Step 1: Create deployment package
echo -e "${YELLOW}[1/5] Creating deployment package...${NC}"
rm -rf deploy_hw_detector hw_detector_v2_deploy.tar.gz 2>/dev/null || true
mkdir -p deploy_hw_detector

cp scripts/detect_hardware_v2.py deploy_hw_detector/
cp docs/HARDWARE_DETECTOR_SPEC.md deploy_hw_detector/
cp docs/AMD_PROFILING_GUIDE.md deploy_hw_detector/
cp docs/DEPLOYMENT_GUIDE.md deploy_hw_detector/
cp tests/test_detect_hardware.py deploy_hw_detector/

cat > deploy_hw_detector/README.txt << 'EOF'
Hardware Detector v2 - Deployment Package
==========================================

Files:
- detect_hardware_v2.py       Main detection script
- test_detect_hardware.py     Test suite
- HARDWARE_DETECTOR_SPEC.md   Technical documentation
- AMD_PROFILING_GUIDE.md      AMD-specific profiling guide
- DEPLOYMENT_GUIDE.md         Full deployment instructions

Quick Start:
1. python detect_hardware_v2.py
2. Check hardware_detect_report.json for results

Testing:
python test_detect_hardware.py --smoke

For full documentation, see DEPLOYMENT_GUIDE.md
EOF

tar czf hw_detector_v2_deploy.tar.gz deploy_hw_detector/
echo -e "${GREEN}✓ Package created: hw_detector_v2_deploy.tar.gz${NC}"

# Step 2: Transfer to cluster
echo -e "${YELLOW}[2/5] Transferring to cluster...${NC}"
scp hw_detector_v2_deploy.tar.gz ${USERNAME}@${CLUSTER}:~/
echo -e "${GREEN}✓ Transfer complete${NC}"

# Step 3: Extract and setup on cluster
echo -e "${YELLOW}[3/5] Extracting on cluster...${NC}"
ssh ${USERNAME}@${CLUSTER} << 'ENDSSH'
cd ~
tar xzf hw_detector_v2_deploy.tar.gz
cd deploy_hw_detector
chmod +x detect_hardware_v2.py
echo "Files extracted to: ~/deploy_hw_detector"
ls -lh
ENDSSH
echo -e "${GREEN}✓ Extraction complete${NC}"

# Step 4: Run smoke test
echo -e "${YELLOW}[4/5] Running smoke test on cluster...${NC}"
ssh ${USERNAME}@${CLUSTER} << 'ENDSSH'
cd ~/deploy_hw_detector
echo "Running smoke test..."
python test_detect_hardware.py --smoke
ENDSSH

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Smoke test passed${NC}"
else
    echo -e "${RED}✗ Smoke test failed - check output above${NC}"
    exit 1
fi

# Step 5: Run full detection
echo -e "${YELLOW}[5/5] Running hardware detection...${NC}"
ssh ${USERNAME}@${CLUSTER} << 'ENDSSH'
cd ~/deploy_hw_detector
echo ""
echo "Running hardware detection..."
echo "================================"
python detect_hardware_v2.py
echo ""
echo "JSON report saved to: ~/deploy_hw_detector/hardware_detect_report.json"
ENDSSH

echo ""
echo -e "${GREEN}=== Deployment Complete! ===${NC}"
echo ""
echo "Next steps:"
echo "1. SSH to cluster: ssh ${USERNAME}@${CLUSTER}"
echo "2. Review results: cd ~/deploy_hw_detector && cat hardware_detect_report.json"
echo "3. Move to project: mv deploy_hw_detector ~/proyecto10/scripts/ (adjust path as needed)"
echo ""
echo "For full deployment guide, see: docs/DEPLOYMENT_GUIDE.md"

# Cleanup local files
rm -rf deploy_hw_detector hw_detector_v2_deploy.tar.gz
