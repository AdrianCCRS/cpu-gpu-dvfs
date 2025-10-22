"""
Hardware detection utility for Proyecto 10
Provides Python interface to CPU/GPU capabilities
"""

import os
import subprocess
import platform
from typing import Dict, List, Optional
import json


class HardwareDetector:
    """Detects and reports system hardware capabilities for DVFS experiments"""
    
    def __init__(self):
        self.info = {}
        self._detect_all()
    
    def _run_command(self, cmd: List[str]) -> Optional[str]:
        """Run shell command and return output"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None
    
    def _detect_all(self):
        """Run all detection methods"""
        self.info['system'] = self._get_system_info()
        self.info['cpu'] = self._get_cpu_info()
        self.info['gpu'] = self._get_gpu_info()
        self.info['capabilities'] = self._get_capabilities()
    
    def _get_system_info(self) -> Dict:
        """Get basic system information"""
        return {
            'hostname': platform.node(),
            'kernel': platform.release(),
            'os': platform.system(),
            'machine': platform.machine()
        }
    
    def _get_cpu_info(self) -> Dict:
        """Get CPU information"""
        cpu_info = {}
        
        # Try lscpu
        lscpu_out = self._run_command(['lscpu'])
        if lscpu_out:
            for line in lscpu_out.split('\n'):
                if 'Model name:' in line:
                    cpu_info['model'] = line.split(':', 1)[1].strip()
                elif 'CPU(s):' in line and 'CPU(s):' == line.split(':')[0]:
                    cpu_info['logical_cpus'] = int(line.split(':')[1].strip())
                elif 'Core(s) per socket:' in line:
                    cpu_info['cores_per_socket'] = int(line.split(':')[1].strip())
        
        # CPU frequency info
        cpufreq_path = "/sys/devices/system/cpu/cpu0/cpufreq"
        if os.path.exists(cpufreq_path):
            try:
                with open(f"{cpufreq_path}/scaling_available_frequencies") as f:
                    freqs = f.read().strip().split()
                    cpu_info['available_frequencies'] = [int(f) for f in freqs]
            except FileNotFoundError:
                # Try cpuinfo_max/min instead
                try:
                    with open(f"{cpufreq_path}/cpuinfo_max_freq") as f:
                        cpu_info['max_freq'] = int(f.read().strip())
                    with open(f"{cpufreq_path}/cpuinfo_min_freq") as f:
                        cpu_info['min_freq'] = int(f.read().strip())
                except Exception:
                    pass
            
            try:
                with open(f"{cpufreq_path}/scaling_available_governors") as f:
                    cpu_info['available_governors'] = f.read().strip().split()
            except Exception:
                pass
        
        return cpu_info
    
    def _get_gpu_info(self) -> Dict:
        """Get GPU information"""
        gpu_info = {'nvidia': [], 'intel': None}
        
        # NVIDIA GPUs
        nvidia_query = self._run_command(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader'])
        if nvidia_query:
            for line in nvidia_query.split('\n'):
                if line.strip():
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 2:
                        gpu_info['nvidia'].append({
                            'name': parts[0],
                            'memory': parts[1] if len(parts) > 1 else 'unknown',
                            'driver': parts[2] if len(parts) > 2 else 'unknown'
                        })
        
        # Intel GPU
        if os.path.exists('/sys/class/drm'):
            drm_devices = os.listdir('/sys/class/drm')
            intel_cards = [d for d in drm_devices if d.startswith('card') and not d.startswith('card0-')]
            if intel_cards:
                gpu_info['intel'] = {'cards': intel_cards}
        
        return gpu_info
    
    def _get_capabilities(self) -> Dict:
        """Check for required capabilities"""
        caps = {}
        
        # RAPL support
        caps['rapl_available'] = os.path.exists('/sys/class/powercap/intel-rapl')
        caps['rapl_readable'] = False
        if caps['rapl_available']:
            try:
                with open('/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj') as f:
                    f.read()
                    caps['rapl_readable'] = True
            except:
                pass
        
        # CPUFreq writable
        caps['cpufreq_writable'] = os.access('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', os.W_OK) if os.path.exists('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor') else False
        
        # Tools available
        caps['tools'] = {
            'perf': self._run_command(['which', 'perf']) is not None,
            'nvidia-smi': self._run_command(['which', 'nvidia-smi']) is not None,
            'intel_gpu_top': self._run_command(['which', 'intel_gpu_top']) is not None,
            'cpupower': self._run_command(['which', 'cpupower']) is not None
        }
        
        return caps
    
    def print_report(self):
        """Print human-readable hardware report"""
        print("=" * 80)
        print("  Hardware Detection Report - Proyecto 10")
        print("=" * 80)
        print()
        
        # System Information
        print("┌─ SYSTEM INFORMATION " + "─" * 58)
        sys = self.info['system']
        print(f"│ Hostname:     {sys['hostname']}")
        print(f"│ OS:           {sys['os']}")
        print(f"│ Kernel:       {sys['kernel']}")
        print(f"│ Architecture: {sys['machine']}")
        print("└" + "─" * 79)
        print()
        
        # CPU Information
        print("┌─ CPU INFORMATION " + "─" * 61)
        cpu = self.info['cpu']
        print(f"│ Model:        {cpu.get('model', 'Unknown')}")
        print(f"│ Logical CPUs: {cpu.get('logical_cpus', 'Unknown')}")
        
        if 'cores_per_socket' in cpu:
            print(f"│ Cores/Socket: {cpu['cores_per_socket']}")
        
        # Frequency information (detailed)
        if 'available_frequencies' in cpu:
            freqs = cpu['available_frequencies']
            print(f"│ Frequencies:  {len(freqs)} discrete levels")
            print(f"│   Range:      {min(freqs)/1000:.2f} GHz - {max(freqs)/1000:.2f} GHz")
            print(f"│   Step:       ~{(max(freqs)-min(freqs))/(len(freqs)-1)/1000:.2f} GHz" if len(freqs) > 1 else "")
            
            # Show all frequencies if not too many
            if len(freqs) <= 15:
                freq_ghz = [f/1000 for f in freqs]
                print(f"│   All freqs:  {', '.join([f'{f:.2f}' for f in freq_ghz])} GHz")
            else:
                # Show first 5 and last 5
                freq_ghz_head = [f/1000 for f in freqs[:5]]
                freq_ghz_tail = [f/1000 for f in freqs[-5:]]
                print(f"│   First 5:    {', '.join([f'{f:.2f}' for f in freq_ghz_head])} GHz")
                print(f"│   Last 5:     {', '.join([f'{f:.2f}' for f in freq_ghz_tail])} GHz")
                print(f"│   (... {len(freqs)-10} more ...)")
                
        elif 'max_freq' in cpu:
            print(f"│ Frequencies:  Continuous range (no discrete steps)")
            print(f"│   Min:        {cpu['min_freq']/1000:.2f} GHz")
            print(f"│   Max:        {cpu['max_freq']/1000:.2f} GHz")
        else:
            print(f"│ Frequencies:  ⚠ Could not detect")
        
        # Governors
        if 'available_governors' in cpu:
            print(f"│ Governors:    {', '.join(cpu['available_governors'])}")
        else:
            print(f"│ Governors:    ⚠ Could not detect")
        
        print("└" + "─" * 79)
        print()
        
        # GPU Information
        print("┌─ GPU INFORMATION " + "─" * 61)
        gpu = self.info['gpu']
        
        if gpu['nvidia']:
            print(f"│ NVIDIA GPUs:  {len(gpu['nvidia'])} detected")
            for i, nv in enumerate(gpu['nvidia']):
                print(f"│   GPU {i}:")
                print(f"│     Name:    {nv['name']}")
                print(f"│     Memory:  {nv['memory']}")
                print(f"│     Driver:  {nv['driver']}")
        else:
            print("│ NVIDIA GPUs:  Not detected")
        
        if gpu['intel']:
            print(f"│ Intel GPU:    Detected")
            print(f"│   Cards:      {', '.join(gpu['intel']['cards'])}")
        else:
            print("│ Intel GPU:    Not detected")
        
        print("└" + "─" * 79)
        print()
        
        # Capabilities
        print("┌─ SYSTEM CAPABILITIES " + "─" * 57)
        caps = self.info['capabilities']
        
        # RAPL
        rapl_status = ""
        if caps['rapl_available']:
            if caps['rapl_readable']:
                rapl_status = "✓ Available and readable"
            else:
                rapl_status = "⚠ Available but NOT readable (needs sudo/permissions)"
        else:
            rapl_status = "✗ Not available (Intel CPU required)"
        print(f"│ RAPL (Energy): {rapl_status}")
        
        # CPUFreq
        cpufreq_status = ""
        if caps['cpufreq_writable']:
            cpufreq_status = "✓ Writable (can change frequencies)"
        else:
            cpufreq_status = "✗ Read-only (needs sudo for frequency control)"
        print(f"│ CPUFreq:       {cpufreq_status}")
        
        print("│")
        
        # Tools
        print("│ Required Tools:")
        tools = caps['tools']
        print(f"│   perf:          {'✓ installed' if tools['perf'] else '✗ NOT installed (apt install linux-tools-generic)'}")
        print(f"│   cpupower:      {'✓ installed' if tools['cpupower'] else '✗ NOT installed (apt install linux-cpupower)'}")
        print(f"│   nvidia-smi:    {'✓ installed' if tools['nvidia-smi'] else '✗ NOT installed (install nvidia drivers)'}")
        print(f"│   intel_gpu_top: {'✓ installed' if tools['intel_gpu_top'] else '✗ NOT installed (apt install intel-gpu-tools)'}")
        
        print("└" + "─" * 79)
        print()
        
        # Warnings and Recommendations
        warnings = []
        if not caps['rapl_readable'] and caps['rapl_available']:
            warnings.append("RAPL needs permissions: sudo chmod -R a+r /sys/class/powercap/intel-rapl/")
        if not caps['cpufreq_writable']:
            warnings.append("Frequency control needs sudo/root privileges")
        if not tools['perf']:
            warnings.append("Install perf: sudo apt-get install linux-tools-$(uname -r)")
        if not tools['cpupower']:
            warnings.append("Install cpupower: sudo apt-get install linux-cpupower")
        
        if warnings:
            print("⚠ WARNINGS & RECOMMENDATIONS:")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")
            print()
        else:
            print("✓ All required capabilities detected!")
            print()
        
        print("=" * 80)
    
    def to_json(self, filepath: str):
        """Save detection results to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.info, f, indent=2)


if __name__ == '__main__':
    detector = HardwareDetector()
    detector.print_report()
    
    # Optionally save to file
    output_file = '../docs/hardware_detection.json'
    if os.path.exists('../docs'):
        detector.to_json(output_file)
        print(f"Saved to {output_file}")
