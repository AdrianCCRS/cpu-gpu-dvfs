#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hardware Detector — Proyecto 10
Read-only, non-intrusive detection of CPU/GPU/topology/capabilities for CentOS7 and Fedora.
Python 3.9+ required.
Produces JSON report and human-readable summary.

Version: 2.1.0
"""

import os
import sys
import json
import socket
import subprocess
import platform
import argparse
import glob
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from shutil import which

__version__ = "2.1.0"
__schema_version__ = "2.1"


def run_cmd(cmd: List[str], timeout: int = 10) -> Tuple[int, str, str]:
    """Run command with timeout and return (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True
        )
        return (result.returncode, result.stdout.strip(), result.stderr.strip())
    except subprocess.TimeoutExpired:
        return (-1, '', 'Command timeout')
    except Exception as e:
        return (-1, '', str(e))


class HardwareDetectorV2:
    """Hardware detection for HPC systems - Python 3.9+"""
    
    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = cache_path
        self.info: Dict[str, Any] = {
            'version': __version__,
            'schema_version': __schema_version__,
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'metadata': {},
            'system': {},
            'cpu': {},
            'numa': {},
            'gpu': {},
            'hwmon': {},
            'capabilities': {},
            'warnings': []
        }
        self._collect_metadata()
        self._detect_system()
        self._detect_cpu()
        self._detect_numa()
        self._detect_gpu()
        self._detect_hwmon()
        self._detect_capabilities()
        self._add_recommendations()

    def _collect_metadata(self):
        self.info['metadata']['hostname'] = socket.gethostname()
        self.info['metadata']['os'] = platform.system()
        try:
            # platform.linux_distribution deprecated in py3 but available in py2
            if hasattr(platform, 'linux_distribution'):
                dist = platform.linux_distribution()
                self.info['metadata']['distribution'] = ' '.join([str(x) for x in dist if x])
            else:
                # Fallback: /etc/os-release
                try:
                    with open('/etc/os-release') as f:
                        lines = f.read().strip().split('\n')
                        dist_info = {}
                        for line in lines:
                            if '=' in line:
                                key, val = line.split('=', 1)
                                dist_info[key] = val.strip('"')
                        self.info['metadata']['distribution'] = dist_info.get('PRETTY_NAME', lines[0] if lines else '')
                except:
                    self.info['metadata']['distribution'] = ''
        except Exception:
            self.info['metadata']['distribution'] = ''
        self.info['metadata']['kernel'] = platform.release()
        self.info['metadata']['python_version'] = platform.python_version()
        
        # Add uname details for reproducibility
        rc, out, err = run_cmd(['uname', '-a'])
        if rc == 0:
            self.info['metadata']['uname_full'] = out

    def _detect_system(self) -> None:
        """Detect system information"""
        self.info['system']['arch'] = platform.machine()
        self.info['system']['uname'] = platform.uname()._asdict()

    def _detect_cpu(self) -> None:
        """Detect CPU information and capabilities"""
        cpu: Dict[str, Any] = {}
        # lscpu output
        rc, out, err = run_cmd(['lscpu'])
        if rc == 0 and out:
            for line in out.split('\n'):
                if ':' not in line:
                    continue
                k, v = line.split(':', 1)
                k = k.strip(); v = v.strip()
                if k == 'Vendor ID':
                    cpu['vendor_id'] = v
                    cpu['vendor'] = 'Intel' if 'GenuineIntel' in v else ('AMD' if 'AuthenticAMD' in v else v)
                elif k == 'Model name':
                    cpu['model'] = v
                elif k == 'CPU(s)':
                    try:
                        cpu['logical_cpus'] = int(v)
                    except:
                        cpu['logical_cpus'] = v
                elif k == 'Socket(s)':
                    cpu['sockets'] = int(v) if v.isdigit() else v
                elif k == 'Core(s) per socket':
                    cpu['cores_per_socket'] = int(v) if v.isdigit() else v
                elif k == 'Thread(s) per core':
                    cpu['threads_per_core'] = int(v) if v.isdigit() else v
        else:
            # fallback to /proc/cpuinfo
            rc, out, err = run_cmd(['cat', '/proc/cpuinfo'])
            if rc == 0 and out:
                for line in out.split('\n'):
                    if 'vendor_id' in line and 'vendor' not in cpu:
                        cpu['vendor_id'] = line.split(':',1)[1].strip()
                        cpu['vendor'] = 'Intel' if 'GenuineIntel' in cpu['vendor_id'] else ('AMD' if 'AuthenticAMD' in cpu['vendor_id'] else cpu['vendor_id'])
                    if 'model name' in line and 'model' not in cpu:
                        cpu['model'] = line.split(':',1)[1].strip()
        # frequency info best-effort (read-only)
        cpu['freq'] = {}
        cpufreq_base = Path('/sys/devices/system/cpu/cpu0/cpufreq')
        if cpufreq_base.exists():
            try:
                driver_file = cpufreq_base / 'scaling_driver'
                if driver_file.exists():
                    cpu['freq']['driver'] = driver_file.read_text().strip()
            except Exception:
                pass
            try:
                gov_file = cpufreq_base / 'scaling_available_governors'
                if gov_file.exists():
                    cpu['freq']['available_governors'] = gov_file.read_text().strip().split()
            except Exception:
                pass
            try:
                freq_file = cpufreq_base / 'scaling_available_frequencies'
                if freq_file.exists():
                    vals = freq_file.read_text().strip().split()
                    if vals:
                        cpu['freq']['available_frequencies'] = [int(x) for x in vals]
            except Exception:
                pass
            # cpuinfo min/max
            try:
                min_file = cpufreq_base / 'cpuinfo_min_freq'
                max_file = cpufreq_base / 'cpuinfo_max_freq'
                if min_file.exists():
                    cpu['freq']['min_khz'] = int(min_file.read_text().strip())
                if max_file.exists():
                    cpu['freq']['max_khz'] = int(max_file.read_text().strip())
            except Exception:
                pass
            
            # Generate suggested frequencies if not available (e.g., pcc-cpufreq)
            if 'available_frequencies' not in cpu['freq'] or not cpu['freq']['available_frequencies']:
                if 'min_khz' in cpu['freq'] and 'max_khz' in cpu['freq']:
                    cpu['freq']['suggested_frequencies'] = self._generate_cpu_frequency_points(
                        cpu['freq']['min_khz'],
                        cpu['freq']['max_khz']
                    )
                    cpu['freq']['frequency_note'] = f"Driver '{cpu['freq'].get('driver', 'unknown')}' does not expose available_frequencies. Suggested sweep points generated from min/max range."
        else:
            cpu['freq']['note'] = 'cpufreq sysfs not present'

        # basic RAPL detection read-only
        rapl_path = Path('/sys/class/powercap')
        cpu['rapl'] = {'available': False, 'readable': False, 'domains': []}
        if rapl_path.exists():
            try:
                # search for intel-rapl entries
                for entry in rapl_path.iterdir():
                    if 'intel-rapl' in entry.name:
                        cpu['rapl']['available'] = True
                        # check for energy_uj files under domain
                        for energy_file in entry.rglob('energy_uj'):
                            cpu['rapl']['domains'].append(str(energy_file))
                            # check readability
                            if os.access(energy_file, os.R_OK):
                                cpu['rapl']['readable'] = True
            except Exception:
                pass
        
                # AMD energy detection (hwmon)
        cpu['amd_energy'] = {'available': False, 'readable': False, 'sensors': [], 'driver': None}
        if cpu.get('vendor') == 'AMD':
            hwmon_path = Path('/sys/class/hwmon')
            if hwmon_path.exists():
                try:
                    for hwmon_dev in hwmon_path.iterdir():
                        name_file = hwmon_dev / 'name'
                        if name_file.exists():
                            try:
                                driver_name = name_file.read_text().strip()
                                if any(x in driver_name for x in ['amd_energy', 'k10temp', 'zenpower']):
                                    cpu['amd_energy']['available'] = True
                                    cpu['amd_energy']['driver'] = driver_name
                                    # check for energy sensors
                                    for energy_file in hwmon_dev.glob('energy*_input'):
                                        cpu['amd_energy']['sensors'].append(str(energy_file))
                                        if os.access(energy_file, os.R_OK):
                                            cpu['amd_energy']['readable'] = True
                            except Exception:
                                continue
                except Exception:
                    pass
        
        # AMD uProf detection
        cpu['amd_uprof'] = {'installed': False, 'version': None, 'path': None, 'capabilities': []}
        if cpu.get('vendor') == 'AMD':
            # Check for AMDuProf installation
            uprof_candidates = [
                *Path('/opt').glob('AMDuProf*/bin/AMDuProfCLI'),
                *Path('/usr/local').glob('AMDuProf*/bin/AMDuProfCLI'),
            ]
            
            # Check PATH
            uprof_cmd = which('AMDuProfCLI')
            if uprof_cmd:
                uprof_candidates.append(Path(uprof_cmd))
            
            for uprof_path in uprof_candidates:
                if uprof_path.exists():
                    cpu['amd_uprof']['installed'] = True
                    cpu['amd_uprof']['path'] = str(uprof_path)
                    # Try to get version
                    try:
                        rc, out, err = run_cmd([str(uprof_path), '--version'], timeout=5)
                        if rc == 0 and out:
                            cpu['amd_uprof']['version'] = out.split('\n')[0].strip()
                    except:
                        pass
                    
                    # Detect available profiling modes
                    cpu['amd_uprof']['capabilities'] = [
                        'energy_profiling',
                        'pmu_counters',
                        'instruction_profiling',
                        'power_profiling'
                    ]
                    break
            
            # Check for AMD MSR driver (needed for advanced profiling)
            msr_dev = Path('/dev/cpu/0/msr')
            if msr_dev.exists():
                cpu['amd_uprof']['msr_available'] = os.access(msr_dev, os.R_OK)
            else:
                cpu['amd_uprof']['msr_available'] = False

        self.info['cpu'] = cpu

    def _detect_numa(self) -> None:
        """Detect NUMA topology"""
        numa: Dict[str, Any] = {}
        if which('numactl'):
            rc, out, err = run_cmd(['numactl', '--hardware'])
            if rc == 0 and out:
                numa['numactl_hw'] = out
                # Parse node count
                nodes = 0
                for line in out.split('\n'):
                    if line.strip().startswith('available:'):
                        try:
                            nodes = int(line.split(':')[1].split()[0])
                        except:
                            nodes = 0
                numa['num_nodes'] = nodes
                
                # Parse per-node CPU mapping
                numa['node_cpus'] = {}
                for line in out.split('\n'):
                    if line.strip().startswith('node') and 'cpus:' in line:
                        try:
                            parts = line.split('cpus:')
                            node_id = parts[0].strip().split()[1]
                            cpus = parts[1].strip()
                            numa['node_cpus']['node_' + node_id] = cpus
                        except:
                            pass
        else:
            numa['note'] = 'numactl not installed'
        self.info['numa'] = numa

    def _detect_gpu(self) -> None:
        """Detect GPU devices"""
        gpu: Dict[str, List[Dict[str, Any]]] = {'nvidia': [], 'amd': [], 'intel': []}
        
        # NVIDIA - try nvidia-smi first
        if which('nvidia-smi'):
            rc, out, err = run_cmd(['nvidia-smi', '--query-gpu=index,name,memory.total,driver_version', '--format=csv,noheader'])
            if rc == 0 and out:
                for line in out.split('\n'):
                    if not line.strip():
                        continue
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 4:
                        entry = {
                            'index': int(parts[0]) if parts[0].isdigit() else parts[0],
                            'name': parts[1],
                            'memory': parts[2],
                            'driver': parts[3],
                            'source': 'nvidia-smi'
                        }
                        gpu['nvidia'].append(entry)
        
        # Detect GPU frequency capabilities for NVIDIA GPUs
        if gpu['nvidia'] and which('nvidia-smi'):
            for gpu_entry in gpu['nvidia']:
                if 'index' in gpu_entry:
                    freq_info = self._detect_nvidia_frequencies(gpu_entry['index'])
                    if freq_info:
                        gpu_entry['frequency_info'] = freq_info
        
        # Fallback: Use lspci if nvidia-smi didn't find GPUs or doesn't exist
        if not gpu['nvidia']:
            self._detect_gpu_via_lspci(gpu)
        
                # AMD (rocm-smi)
        if which('rocm-smi'):
            rc, out, err = run_cmd(['rocm-smi', '--showproductname'])
            if rc == 0 and out:
                gpu['amd'].append({'rocm_smi': out.split('\n')[0]})
        
        # Intel GPU via DRM
        drm_path = Path('/sys/class/drm')
        if drm_path.exists():
            for card_dir in drm_path.glob('card*'):
                # avoid listing connectors like card0-HDMI-A-1
                if '-' in card_dir.name:
                    continue
                
                intel_entry = {'card': card_dir.name}
                
                # try typical sysfs freq nodes
                rps_path = card_dir / 'gt' / 'rps'
                if rps_path.exists():
                    try:
                        cur_freq = rps_path / 'cur_freq'
                        if cur_freq.exists():
                            intel_entry['cur_freq'] = cur_freq.read_text().strip()
                    except Exception:
                        pass
                    try:
                        min_freq = rps_path / 'min_freq'
                        if min_freq.exists():
                            intel_entry['min_freq'] = min_freq.read_text().strip()
                    except Exception:
                        pass
                    try:
                        max_freq = rps_path / 'max_freq'
                        if max_freq.exists():
                            intel_entry['max_freq'] = max_freq.read_text().strip()
                    except Exception:
                        pass
                
                if len(intel_entry) > 1:  # more than just 'card'
                    gpu['intel'].append(intel_entry)

        self.info['gpu'] = gpu
    
    def _detect_nvidia_frequencies(self, gpu_id: int) -> Optional[Dict[str, Any]]:
        """
        Detect NVIDIA GPU frequency information using nvidia-smi SUPPORTED_CLOCKS.
        
        Args:
            gpu_id: GPU index (0-7)
            
        Returns:
            Dictionary with frequency info, or None if detection fails
        """
        freq_info = {
            'method': None,
            'supported_clocks': None,
            'notes': []
        }
        
        # Try nvidia-smi -q -d SUPPORTED_CLOCKS
        try:
            cmd = ['nvidia-smi', '-i', str(gpu_id), '-q', '-d', 'SUPPORTED_CLOCKS']
            rc, out, err = run_cmd(cmd)
            
            if rc == 0 and out and 'N/A' not in out:
                # Parse supported clocks output
                freq_info['method'] = 'nvidia-smi -q -d SUPPORTED_CLOCKS'
                freq_info['supported_clocks'] = self._parse_supported_clocks(out)
                if freq_info['supported_clocks']:
                    return freq_info
            else:
                freq_info['notes'].append('nvidia-smi SUPPORTED_CLOCKS returned N/A or not available on this driver')
        except Exception as e:
            freq_info['notes'].append(f'nvidia-smi SUPPORTED_CLOCKS failed: {e}')
        
        return None
    
    def _parse_supported_clocks(self, output: str) -> Optional[List[Dict[str, int]]]:
        """
        Parse nvidia-smi SUPPORTED_CLOCKS output.
        
        Returns:
            List of {memory_mhz, graphics_mhz} dicts
        """
        clocks = []
        current_mem = None
        
        for line in output.split('\n'):
            line = line.strip()
            
            # Look for "Memory : XXXX MHz"
            if line.startswith('Memory'):
                parts = line.split(':')
                if len(parts) >= 2:
                    try:
                        current_mem = int(parts[1].strip().split()[0])
                    except (ValueError, IndexError):
                        pass
            
            # Look for "Graphics : XXXX MHz"
            elif line.startswith('Graphics') and current_mem:
                parts = line.split(':')
                if len(parts) >= 2:
                    try:
                        graphics = int(parts[1].strip().split()[0])
                        clocks.append({
                            'memory_mhz': current_mem,
                            'graphics_mhz': graphics
                        })
                    except (ValueError, IndexError):
                        pass
        
        return clocks if clocks else None
    
    def _generate_cpu_frequency_points(self, min_khz: int, max_khz: int, num_points: int = 5) -> List[int]:
        """
        Generate evenly spaced CPU frequency points for sweep.
        
        Args:
            min_khz: Minimum frequency in kHz
            max_khz: Maximum frequency in kHz
            num_points: Number of frequency points to generate (default: 5)
            
        Returns:
            List of frequencies in kHz, evenly distributed
        """
        if min_khz >= max_khz:
            return [min_khz]
        
        step = (max_khz - min_khz) / (num_points - 1)
        freqs = [int(min_khz + i * step) for i in range(num_points)]
        
        # Round to nearest 100 MHz for cleaner values
        freqs = [round(f / 100000) * 100000 for f in freqs]
        
        # Ensure min and max are included
        freqs[0] = min_khz
        freqs[-1] = max_khz
        
        return freqs

    def _detect_gpu_via_lspci(self, gpu: Dict[str, List[Dict[str, Any]]]) -> None:
        """Fallback GPU detection using lspci (works without nvidia-smi)"""
        if which('lspci'):
            rc, out, err = run_cmd(['lspci'])
            if rc == 0 and out:
                for line in out.split('\n'):
                    line_lower = line.lower()
                    
                    # NVIDIA detection
                    if 'nvidia' in line_lower and ('vga' in line_lower or '3d' in line_lower or 'display' in line_lower):
                        # Parse lspci line: "08:00.0 3D controller: NVIDIA Corporation GF100GL [Tesla T20 Processor] (rev a3)"
                        parts = line.split(':', 2)
                        if len(parts) >= 3:
                            gpu_name = parts[2].strip()
                            # Extract model name (remove revision info)
                            if '(rev' in gpu_name:
                                gpu_name = gpu_name.split('(rev')[0].strip()
                            
                            entry = {
                                'name': gpu_name,
                                'bus_id': parts[0].strip(),
                                'source': 'lspci',
                                'note': 'Limited info - nvidia-smi not available or not working'
                            }
                            gpu['nvidia'].append(entry)
                    
                    # AMD detection
                    elif ('amd' in line_lower or 'ati' in line_lower) and ('vga' in line_lower or '3d' in line_lower or 'display' in line_lower):
                        # Skip non-GPU AMD devices (like ES1000 VGA controller used for remote management)
                        if 'es1000' in line_lower:
                            continue
                        parts = line.split(':', 2)
                        if len(parts) >= 3:
                            gpu_name = parts[2].strip()
                            if '(rev' in gpu_name:
                                gpu_name = gpu_name.split('(rev')[0].strip()
                            
                            # Check if it's a real GPU (Radeon, Instinct, etc.) or management controller
                            if any(x in line_lower for x in ['radeon', 'instinct', 'vega', 'navi', 'polaris']):
                                entry = {
                                    'name': gpu_name,
                                    'bus_id': parts[0].strip(),
                                    'source': 'lspci',
                                    'note': 'Limited info - rocm-smi not available'
                                }
                                gpu['amd'].append(entry)
                    
                    # Intel discrete GPU detection (Arc, etc.)
                    elif 'intel' in line_lower and ('vga' in line_lower or '3d' in line_lower or 'display' in line_lower):
                        # Skip integrated graphics chipsets, focus on discrete GPUs
                        if any(x in line_lower for x in ['arc', 'xe', 'dg']):
                            parts = line.split(':', 2)
                            if len(parts) >= 3:
                                gpu_name = parts[2].strip()
                                if '(rev' in gpu_name:
                                    gpu_name = gpu_name.split('(rev')[0].strip()
                                
                                entry = {
                                    'name': gpu_name,
                                    'bus_id': parts[0].strip(),
                                    'source': 'lspci'
                                }
                                gpu['intel'].append(entry)

    def _detect_hwmon(self):
        """Detect hwmon sensors for temperature and power monitoring"""
        hwmon = {'sensors': [], 'readable': False}
        hwmon_path = '/sys/class/hwmon'
        if os.path.exists(hwmon_path):
            try:
                for hwmon_dev in os.listdir(hwmon_path):
                    sensor_info = {'device': hwmon_dev}
                    hwmon_dev_path = os.path.join(hwmon_path, hwmon_dev)
                    
                    # Read sensor name
                    name_file = os.path.join(hwmon_dev_path, 'name')
                    if os.path.exists(name_file):
                        try:
                            with open(name_file) as f:
                                sensor_info['name'] = f.read().strip()
                        except:
                            pass
                    
                    # Detect temperature sensors
                    sensor_info['temps'] = []
                    for entry in os.listdir(hwmon_dev_path):
                        if entry.startswith('temp') and entry.endswith('_input'):
                            temp_file = os.path.join(hwmon_dev_path, entry)
                            try:
                                with open(temp_file) as f:
                                    f.read()
                                    sensor_info['temps'].append(entry)
                                    hwmon['readable'] = True
                            except:
                                pass
                    
                    # Detect power sensors
                    sensor_info['power'] = []
                    for entry in os.listdir(hwmon_dev_path):
                        if entry.startswith('power') and entry.endswith('_input'):
                            power_file = os.path.join(hwmon_dev_path, entry)
                            try:
                                with open(power_file) as f:
                                    f.read()
                                    sensor_info['power'].append(entry)
                                    hwmon['readable'] = True
                            except:
                                pass
                    
                    if len(sensor_info) > 1:  # more than just 'device'
                        hwmon['sensors'].append(sensor_info)
            except Exception:
                pass
        
        self.info['hwmon'] = hwmon

    def _detect_capabilities(self) -> None:
        """Detect system capabilities and tool availability"""
        caps: Dict[str, Any] = {}
        # tools
        tools = ['perf', 'cpupower', 'turbostat', 'numactl', 'nvidia-smi', 'rocm-smi', 'intel_gpu_top']
        caps['tools'] = {tool: bool(which(tool)) for tool in tools}
        
        # permissions
        caps['permissions'] = {}
        caps['permissions']['is_root'] = os.geteuid() == 0
        
        # cpufreq writable?
        cpufreq_gov = Path('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor')
        caps['permissions']['can_write_cpufreq'] = cpufreq_gov.exists() and os.access(cpufreq_gov, os.W_OK)
        # rapl readable (already detected in cpu)
        caps['rapl_readable'] = self.info.get('cpu', {}).get('rapl', {}).get('readable', False)
        # amd energy readable
        caps['amd_energy_readable'] = self.info.get('cpu', {}).get('amd_energy', {}).get('readable', False)
        # hwmon readable
        caps['hwmon_readable'] = self.info.get('hwmon', {}).get('readable', False)
        # ipmi available
        caps['ipmitool'] = bool(which('ipmitool'))
        self.info['capabilities'] = caps

    def _add_recommendations(self) -> None:
        """Add warnings and recommendations based on detected capabilities"""
        warnings: List[str] = []
        
        # Energy monitoring warnings
        cpu_vendor = self.info.get('cpu', {}).get('vendor', '')
        if cpu_vendor == 'Intel':
            if not self.info.get('cpu', {}).get('rapl', {}).get('readable', False):
                warnings.append('RAPL not readable: Intel energy counters unavailable. Consider running as root or adjusting permissions.')
        elif cpu_vendor == 'AMD':
            amd_energy = self.info.get('cpu', {}).get('amd_energy', {})
            amd_uprof = self.info.get('cpu', {}).get('amd_uprof', {})
            
            if not amd_energy.get('readable', False):
                warnings.append('AMD energy sensors not readable. Check hwmon permissions or install zenpower/k10temp drivers.')
            
            if not amd_uprof.get('installed', False):
                warnings.append('AMD uProf not installed: highly recommended for advanced AMD CPU/energy profiling. Download from AMD website.')
            elif amd_uprof.get('installed') and not amd_uprof.get('msr_available', False):
                warnings.append('AMD uProf installed but MSR access not available. May need root permissions or msr kernel module.')
        
        # GPU warnings
        if which('nvidia-smi') and not self.info.get('gpu', {}).get('nvidia'):
            warnings.append('nvidia-smi found but no GPUs detected. Check driver installation.')
        
        if cpu_vendor == 'AMD' and not which('rocm-smi'):
            if self.info.get('gpu', {}).get('amd'):
                warnings.append('AMD GPU detected but rocm-smi not found. Install ROCm for GPU profiling.')
        
        # NUMA warnings
        if self.info.get('cpu', {}).get('sockets', 1) > 1 and not which('numactl'):
            warnings.append('Multi-socket system detected but numactl not installed. Install numactl for NUMA awareness.')
        
        # Tool recommendations
        if not which('perf'):
            warnings.append('perf not found: install linux-tools for CPU profiling capabilities.')
        
        if not which('turbostat') and cpu_vendor == 'Intel':
            warnings.append('turbostat not found: useful for detailed Intel CPU power/frequency monitoring.')
        
        self.info['warnings'] = warnings

    def print_report(self) -> None:
        """Print human-readable hardware report"""
        print(f'--- Proyecto10 Hardware Detection v{__version__} (schema {__schema_version__}) ---')
        md = self.info.get('metadata', {})
        print(f"Host: {md.get('hostname','')}   Distro: {md.get('distribution','')}   Kernel: {md.get('kernel','')}")
        print('\nCPU:')
        cpu = self.info.get('cpu', {})
        print(f"  Vendor: {cpu.get('vendor','Unknown')}  Model: {cpu.get('model','Unknown')}")
        print(f"  Logical CPUs: {cpu.get('logical_cpus','?')}  Sockets: {cpu.get('sockets','?')}  Cores/socket: {cpu.get('cores_per_socket','?')}")
        f = cpu.get('freq', {})
        if 'available_frequencies' in f:
            freqs = f['available_frequencies']
            print(f'  CPU Frequencies: {len(freqs)} levels ({min(freqs)/1000000.0:.2f} GHz - {max(freqs)/1000000.0:.2f} GHz)')
        else:
            if 'min_khz' in f and 'max_khz' in f:
                print(f"  CPU freq range: {f['min_khz']/1000000.0:.2f} GHz - {f['max_khz']/1000000.0:.2f} GHz")
            else:
                print('  CPU frequency info: not available')
        print('\nEnergy Monitoring:')
        print(f"  RAPL: available: {cpu.get('rapl',{}).get('available',False)}  readable: {cpu.get('rapl',{}).get('readable',False)}")
        if cpu.get('vendor') == 'AMD':
            amd_energy = cpu.get('amd_energy', {})
            print(f"  AMD Energy (hwmon): available: {amd_energy.get('available', False)}  readable: {amd_energy.get('readable', False)}")
            if amd_energy.get('driver'):
                print(f"    driver: {amd_energy.get('driver')}")
            
            amd_uprof = cpu.get('amd_uprof', {})
            if amd_uprof.get('installed'):
                print(f"  AMD uProf: installed: True  version: {amd_uprof.get('version', 'unknown')}")
                print(f"    path: {amd_uprof.get('path', 'N/A')}")
                print(f"    MSR readable: {amd_uprof.get('msr_available', False)}")
                if amd_uprof.get('capabilities'):
                    print(f"    capabilities: {', '.join(amd_uprof.get('capabilities', []))}")
            else:
                print('  AMD uProf: not installed (recommended for advanced AMD profiling)')
        
        print('\nNUMA:')
        numa = self.info.get('numa', {})
        print(f"  numactl: {'installed' if 'numactl_hw' in numa else 'not installed'}")
        if 'num_nodes' in numa:
            print(f"  nodes detected: {numa['num_nodes']}")

        print('\nGPU:')
        gpu = self.info.get('gpu', {})
        if gpu.get('nvidia'):
            print(f"  NVIDIA GPUs detected: {len(gpu.get('nvidia'))}")
            for g in gpu.get('nvidia'):
                if g.get('source') == 'nvidia-smi':
                    gpu_id = f"[GPU {g.get('index')}] " if 'index' in g else ''
                    print(f"   - {gpu_id}{g.get('name')}  mem:{g.get('memory', 'N/A')} driver:{g.get('driver', 'N/A')}")
                else:
                    # lspci source
                    print(f"   - {g.get('name')}  bus:{g.get('bus_id', 'N/A')} (detected via lspci)")
        else:
            print('  NVIDIA GPUs: none detected')
        if gpu.get('amd'):
            print(f"  AMD GPUs detected: {len(gpu.get('amd'))}")
            for g in gpu.get('amd'):
                if 'bus_id' in g:
                    print(f"   - {g.get('name')}  bus:{g.get('bus_id')}")
                else:
                    print(f"   - {g.get('name', g.get('rocm_smi', 'Unknown'))}")
        if gpu.get('intel'):
            print(f"  Intel GPU cards: {len(gpu.get('intel'))}")
            for g in gpu.get('intel'):
                if 'bus_id' in g:
                    print(f"   - {g.get('name')}  bus:{g.get('bus_id')}")
                else:
                    print(f"   - {g.get('card', 'Unknown')}")

        print('\nHardware Monitoring:')
        hwmon = self.info.get('hwmon', {})
        print(f"  hwmon sensors: {len(hwmon.get('sensors', []))}  readable: {hwmon.get('readable', False)}")

        print('\nCapabilities:')
        caps = self.info.get('capabilities', {})
        tools_present = [k for k, v in caps.get('tools', {}).items() if v]
        tools_missing = [k for k, v in caps.get('tools', {}).items() if not v]
        print(f"  Tools present: {', '.join(tools_present) if tools_present else 'none'}")
        if tools_missing:
            print(f"  Tools missing: {', '.join(tools_missing)}")
        print(f"  is_root: {caps.get('permissions',{}).get('is_root', False)}")
        print(f"  can_write_cpufreq: {caps.get('permissions',{}).get('can_write_cpufreq', False)}")
        
        # Print warnings
        warnings = self.info.get('warnings', [])
        if warnings:
            print('\nWARNINGS & RECOMMENDATIONS:')
            for i, w in enumerate(warnings, 1):
                print(f'  {i}. {w}')
        
        print('-------------------------------------------')

    def to_json(self, path: Path) -> bool:
        """Save detection results to JSON file"""
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.info, indent=2))
            return True
        except Exception as e:
            print(f"Error saving JSON: {e}", file=sys.stderr)
            return False


def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description=f'Hardware Detector v{__version__} - Read-only hardware detection for HPC systems',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python3 detect_hardware_v2.py
  python3 detect_hardware_v2.py --output-dir /path/to/output
  python3 detect_hardware_v2.py -o ./results --quiet
  python3 detect_hardware_v2.py --json-only
        '''
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__} (schema {__schema_version__})'
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=Path,
        default=None,
        help='Directory to save the JSON report (default: script directory)'
    )
    parser.add_argument(
        '-f', '--filename',
        type=str,
        default='hardware_detect_report.json',
        help='Filename for the JSON report (default: hardware_detect_report.json)'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress console report, only save JSON'
    )
    parser.add_argument(
        '--json-only',
        action='store_true',
        help='Only output JSON to stdout, no file saving or console report'
    )
    
    args = parser.parse_args()
    
    det = HardwareDetectorV2()
    
    # Handle json-only mode
    if args.json_only:
        print(json.dumps(det.info, indent=2))
        return 0
    
    # Print console report unless quiet mode
    if not args.quiet:
        det.print_report()
    
    # Determine output path
    if args.output_dir:
        output_path = args.output_dir / args.filename
    else:
        # Save JSON next to script if no output dir specified
        script_dir = Path(__file__).parent
        output_path = script_dir / args.filename
    
    saved = det.to_json(output_path)
    if saved:
        if not args.quiet:
            print(f'Saved JSON to {output_path}')
        return 0
    else:
        print('Could not save JSON (permissions?)', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
