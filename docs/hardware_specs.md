# Hardware Specifications

This file will contain detailed hardware specifications for the experimental platforms.

## Template

```
Platform: [name]
Date: [YYYY-MM-DD]

### CPU
- Model: 
- Cores: 
- Threads: 
- Base Frequency: 
- Max Turbo: 
- Available Frequencies: 
- Cache: L1/L2/L3

### GPU
- Model: 
- Compute Capability: 
- Memory: 
- CUDA Cores / Execution Units: 
- Base/Boost Clock: 

### Memory
- Capacity: 
- Type: 
- Speed: 

### Power Measurement
- RAPL Domains: 
- External Power Meter: 

### Software Environment
- OS: 
- Kernel: 
- NVIDIA Driver: 
- CUDA Version: 
```

Run `./scripts/detect_hardware.sh` to populate this file automatically.
