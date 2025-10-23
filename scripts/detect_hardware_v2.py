#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hardware Detector v2 — Proyecto 10
Read-only, non-intrusive detection of CPU/GPU/topology/capabilities for CentOS7 and Fedora.
Compatible with Python 2.7+ (avoid f-strings, use .format).
Produces JSON report and human-readable summary.
"""

from __future__ import print_function
import os
import sys
import subprocess
import platform
import json
import time
import socket

# Python2/3 compatibility helpers
try:
    from shutil import which
except ImportError:
    # python2 fallback
    def which(cmd):
        for path in os.environ.get('PATH', '').split(os.pathsep):
            binpath = os.path.join(path, cmd)
            if os.path.exists(binpath) and os.access(binpath, os.X_OK):
                return binpath
        return None

# Small helper to run commands with timeout (simple)
def run_cmd(cmd, timeout=10):
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        returncode = p.returncode
        try:
            if out is None:
                out = ''
            if isinstance(out, bytes):
                out = out.decode('utf-8', 'ignore')
        except Exception:
            out = str(out)
        return (returncode, out.strip(), err.strip() if err else '')
    except Exception as e:
        return (-1, '', str(e))


class HardwareDetectorV2(object):
    SCHEMA_VERSION = '2.0'

    def __init__(self, cache_path=None):
        self.cache_path = cache_path
        self.info = {
            'schema_version': self.SCHEMA_VERSION,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
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

    def _detect_system(self):
        self.info['system']['arch'] = platform.machine()
        self.info['system']['uname'] = platform.uname()

    def _detect_cpu(self):
        cpu = {}
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
        cpufreq_base = '/sys/devices/system/cpu/cpu0/cpufreq'
        if os.path.exists(cpufreq_base):
            try:
                path = os.path.join(cpufreq_base, 'scaling_driver')
                if os.path.exists(path):
                    with open(path) as f:
                        cpu['freq']['driver'] = f.read().strip()
            except Exception:
                pass
            try:
                path = os.path.join(cpufreq_base, 'scaling_available_governors')
                if os.path.exists(path):
                    with open(path) as f:
                        cpu['freq']['available_governors'] = f.read().strip().split()
            except Exception:
                pass
            try:
                path = os.path.join(cpufreq_base, 'scaling_available_frequencies')
                if os.path.exists(path):
                    with open(path) as f:
                        vals = f.read().strip().split()
                        if vals:
                            cpu['freq']['available_frequencies'] = [int(x) for x in vals]
            except Exception:
                pass
            # cpuinfo min/max
            try:
                pathmin = os.path.join(cpufreq_base, 'cpuinfo_min_freq')
                pathmax = os.path.join(cpufreq_base, 'cpuinfo_max_freq')
                if os.path.exists(pathmin):
                    with open(pathmin) as f:
                        cpu['freq']['min_khz'] = int(f.read().strip())
                if os.path.exists(pathmax):
                    with open(pathmax) as f:
                        cpu['freq']['max_khz'] = int(f.read().strip())
            except Exception:
                pass
        else:
            cpu['freq']['note'] = 'cpufreq sysfs not present'

        # basic RAPL detection read-only
        rapl_path = '/sys/class/powercap'
        cpu['rapl'] = {'available': False, 'readable': False, 'domains': []}
        if os.path.exists(rapl_path):
            try:
                # search for intel-rapl entries
                for name in os.listdir(rapl_path):
                    if 'intel-rapl' in name:
                        cpu['rapl']['available'] = True
                        domain = os.path.join(rapl_path, name)
                        # check for energy_uj files under domain
                        for root, dirs, files in os.walk(domain):
                            for f in files:
                                if f.startswith('energy_') and f.endswith('uj'):
                                    energy_file = os.path.join(root, f)
                                    cpu['rapl']['domains'].append(energy_file)
                                    # test readability
                                    try:
                                        with open(energy_file) as fh:
                                            fh.read()
                                            cpu['rapl']['readable'] = True
                                    except Exception:
                                        pass
            except Exception:
                pass
        
        # AMD energy detection (hwmon)
        cpu['amd_energy'] = {'available': False, 'readable': False, 'sensors': [], 'driver': None}
        if cpu.get('vendor') == 'AMD':
            hwmon_path = '/sys/class/hwmon'
            if os.path.exists(hwmon_path):
                try:
                    for hwmon in os.listdir(hwmon_path):
                        name_file = os.path.join(hwmon_path, hwmon, 'name')
                        if os.path.exists(name_file):
                            try:
                                with open(name_file) as f:
                                    name = f.read().strip()
                                    if 'k10temp' in name or 'fam' in name or 'zenpower' in name:
                                        cpu['amd_energy']['available'] = True
                                        cpu['amd_energy']['driver'] = name
                                        # look for energy inputs
                                        hwmon_dir = os.path.join(hwmon_path, hwmon)
                                        for entry in os.listdir(hwmon_dir):
                                            if entry.startswith('energy') and '_input' in entry:
                                                energy_file = os.path.join(hwmon_dir, entry)
                                                cpu['amd_energy']['sensors'].append(energy_file)
                                                try:
                                                    with open(energy_file) as ef:
                                                        ef.read()
                                                        cpu['amd_energy']['readable'] = True
                                                except Exception:
                                                    pass
                            except Exception:
                                pass
                except Exception:
                    pass
        
        # AMD uProf detection
        cpu['amd_uprof'] = {'installed': False, 'version': None, 'path': None, 'capabilities': []}
        if cpu.get('vendor') == 'AMD':
            # Check for AMDuProf installation
            uprof_paths = [
                '/opt/AMDuProf*/bin/AMDuProfCLI',
                '/usr/local/AMDuProf*/bin/AMDuProfCLI',
                which('AMDuProfCLI')
            ]
            for uprof_pattern in uprof_paths:
                if uprof_pattern and '*' in uprof_pattern:
                    # Try glob pattern
                    try:
                        import glob
                        matches = glob.glob(uprof_pattern)
                        if matches:
                            uprof_pattern = matches[0]
                    except:
                        continue
                
                if uprof_pattern and os.path.exists(uprof_pattern):
                    cpu['amd_uprof']['installed'] = True
                    cpu['amd_uprof']['path'] = uprof_pattern
                    # Try to get version
                    try:
                        rc, out, err = run_cmd([uprof_pattern, '--version'], timeout=5)
                        if rc == 0 and out:
                            cpu['amd_uprof']['version'] = out.split('\n')[0].strip()
                    except:
                        pass
                    
                    # Detect available profiling modes
                    # uProf supports: timechart, collect (PMU events), translate
                    cpu['amd_uprof']['capabilities'] = [
                        'energy_profiling',
                        'pmu_counters',
                        'instruction_profiling',
                        'power_profiling'
                    ]
                    break
            
            # Check for AMD MSR driver (needed for advanced profiling)
            msr_dev = '/dev/cpu/0/msr'
            if os.path.exists(msr_dev):
                cpu['amd_uprof']['msr_available'] = os.access(msr_dev, os.R_OK)
            else:
                cpu['amd_uprof']['msr_available'] = False

        self.info['cpu'] = cpu

    def _detect_numa(self):
        # NUMA detection best-effort without root
        numa = {}
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

    def _detect_gpu(self):
        gpu = {'nvidia': [], 'amd': [], 'intel': []}
        
        # NVIDIA - try nvidia-smi first
        if which('nvidia-smi'):
            rc, out, err = run_cmd(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader'])
            if rc == 0 and out:
                for line in out.split('\n'):
                    if not line.strip():
                        continue
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 3:
                        entry = {
                            'name': parts[0],
                            'memory': parts[1],
                            'driver': parts[2],
                            'source': 'nvidia-smi'
                        }
                        gpu['nvidia'].append(entry)
        
        # Fallback: Use lspci if nvidia-smi didn't find GPUs or doesn't exist
        if not gpu['nvidia']:
            self._detect_gpu_via_lspci(gpu)
        
        # AMD (rocm-smi)
        if which('rocm-smi'):
            rc, out, err = run_cmd(['rocm-smi', '--showproductname'])
            if rc == 0 and out:
                gpu['amd'].append({'rocm_smi': out.split('\n')[0]})
        # Intel GPU via DRM
        drm = '/sys/class/drm'
        if os.path.exists(drm):
            devs = [d for d in os.listdir(drm) if d.startswith('card')]
            if devs:
                for d in devs:
                    # avoid listing connectors like card0-HDMI-A-1
                    if '-' in d:
                        continue
                    # try to read gt/ info if present
                    gtpath = os.path.join(drm, d, 'gt')
                    intel_entry = {'card': d}
                    # try typical sysfs freq nodes
                    try:
                        curf = os.path.join('/sys/class/drm', d, 'gt', 'rps', 'cur_freq')
                        if os.path.exists(curf):
                            with open(curf) as f:
                                intel_entry['freq_cur_mhz'] = int(f.read().strip())
                    except Exception:
                        pass
                    try:
                        minf = os.path.join('/sys/class/drm', d, 'gt', 'rps', 'min_freq')
                        if os.path.exists(minf):
                            with open(minf) as f:
                                intel_entry['freq_min_mhz'] = int(f.read().strip())
                    except Exception:
                        pass
                    try:
                        maxf = os.path.join('/sys/class/drm', d, 'gt', 'rps', 'max_freq')
                        if os.path.exists(maxf):
                            with open(maxf) as f:
                                intel_entry['freq_max_mhz'] = int(f.read().strip())
                    except Exception:
                        pass
                    if len(intel_entry) > 1:  # more than just 'card'
                        gpu['intel'].append(intel_entry)

        self.info['gpu'] = gpu

    def _detect_gpu_via_lspci(self, gpu):
        """Fallback GPU detection using lspci (works without nvidia-smi)"""
        # Try lspci
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

    def _detect_capabilities(self):
        caps = {}
        # tools
        tools = ['perf', 'cpupower', 'turbostat', 'numactl', 'nvidia-smi', 'rocm-smi', 'intel_gpu_top', 'ipmitool']
        caps['tools'] = {}
        for t in tools:
            caps['tools'][t] = bool(which(t))
        # permissions
        caps['permissions'] = {}
        caps['permissions']['is_root'] = (os.geteuid() == 0) if hasattr(os, 'geteuid') else False
        # cpufreq writable? (read-only detection only)
        cpufreq_gov = '/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'
        caps['permissions']['can_write_cpufreq'] = os.access(cpufreq_gov, os.W_OK) if os.path.exists(cpufreq_gov) else False
        # rapl readable (already detected in cpu)
        caps['rapl_readable'] = self.info.get('cpu', {}).get('rapl', {}).get('readable', False)
        # amd energy readable
        caps['amd_energy_readable'] = self.info.get('cpu', {}).get('amd_energy', {}).get('readable', False)
        # hwmon readable
        caps['hwmon_readable'] = self.info.get('hwmon', {}).get('readable', False)
        # ipmi available
        caps['ipmitool'] = bool(which('ipmitool'))
        self.info['capabilities'] = caps

    def _add_recommendations(self):
        """Add warnings and recommendations based on detected capabilities"""
        warnings = []
        
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

    def print_report(self):
        # concise summary for HPC audit-only usage
        print('--- Proyecto10 Hardware Detection (v2) ---')
        md = self.info.get('metadata', {})
        print('Host: {0}   Distro: {1}   Kernel: {2}'.format(md.get('hostname',''), md.get('distribution',''), md.get('kernel','')))
        print('\nCPU:')
        cpu = self.info.get('cpu', {})
        print('  Vendor: {0}  Model: {1}'.format(cpu.get('vendor','Unknown'), cpu.get('model','Unknown')))
        print('  Logical CPUs: {0}  Sockets: {1}  Cores/socket: {2}'.format(cpu.get('logical_cpus','?'), cpu.get('sockets','?'), cpu.get('cores_per_socket','?')))
        f = cpu.get('freq', {})
        if 'available_frequencies' in f:
            freqs = f['available_frequencies']
            print('  CPU Frequencies: {0} levels ({1:.2f} GHz - {2:.2f} GHz)'.format(len(freqs), min(freqs)/1000000.0, max(freqs)/1000000.0))
        else:
            if 'min_khz' in f and 'max_khz' in f:
                print('  CPU freq range: {0:.2f} GHz - {1:.2f} GHz'.format(f['min_khz']/1000000.0, f['max_khz']/1000000.0))
            else:
                print('  CPU frequency info: not available')
        print('\nEnergy Monitoring:')
        print('  RAPL: available: {0}  readable: {1}'.format(cpu.get('rapl',{}).get('available',False), cpu.get('rapl',{}).get('readable',False)))
        if cpu.get('vendor') == 'AMD':
            amd_energy = cpu.get('amd_energy', {})
            print('  AMD Energy (hwmon): available: {0}  readable: {1}'.format(
                amd_energy.get('available', False), 
                amd_energy.get('readable', False)
            ))
            if amd_energy.get('driver'):
                print('    driver: {0}'.format(amd_energy.get('driver')))
            
            amd_uprof = cpu.get('amd_uprof', {})
            if amd_uprof.get('installed'):
                print('  AMD uProf: installed: True  version: {0}'.format(amd_uprof.get('version', 'unknown')))
                print('    path: {0}'.format(amd_uprof.get('path', 'N/A')))
                print('    MSR readable: {0}'.format(amd_uprof.get('msr_available', False)))
                if amd_uprof.get('capabilities'):
                    print('    capabilities: {0}'.format(', '.join(amd_uprof.get('capabilities', []))))
            else:
                print('  AMD uProf: not installed (recommended for advanced AMD profiling)')
        
        print('\nNUMA:')
        numa = self.info.get('numa', {})
        print('  numactl: {0}'.format('installed' if 'numactl_hw' in numa else 'not installed'))
        if 'num_nodes' in numa:
            print('  nodes detected: {0}'.format(numa['num_nodes']))

        print('\nGPU:')
        gpu = self.info.get('gpu', {})
        if gpu.get('nvidia'):
            print('  NVIDIA GPUs detected: {0}'.format(len(gpu.get('nvidia'))))
            for g in gpu.get('nvidia'):
                if g.get('source') == 'nvidia-smi':
                    print('   - {0}  mem:{1} driver:{2}'.format(g.get('name'), g.get('memory', 'N/A'), g.get('driver', 'N/A')))
                else:
                    # lspci source
                    print('   - {0}  bus:{1} (detected via lspci)'.format(g.get('name'), g.get('bus_id', 'N/A')))
        else:
            print('  NVIDIA GPUs: none detected')
        if gpu.get('amd'):
            print('  AMD GPUs detected: {0}'.format(len(gpu.get('amd'))))
            for g in gpu.get('amd'):
                if 'bus_id' in g:
                    print('   - {0}  bus:{1}'.format(g.get('name'), g.get('bus_id')))
                else:
                    print('   - {0}'.format(g.get('name', g.get('rocm_smi', 'Unknown'))))
        if gpu.get('intel'):
            print('  Intel GPU cards: {0}'.format(len(gpu.get('intel'))))
            for g in gpu.get('intel'):
                if 'bus_id' in g:
                    print('   - {0}  bus:{1}'.format(g.get('name'), g.get('bus_id')))
                else:
                    print('   - {0}'.format(g.get('card', 'Unknown')))

        print('\nHardware Monitoring:')
        hwmon = self.info.get('hwmon', {})
        print('  hwmon sensors: {0}  readable: {1}'.format(len(hwmon.get('sensors', [])), hwmon.get('readable', False)))

        print('\nCapabilities:')
        caps = self.info.get('capabilities', {})
        tools_present = [k for k, v in caps.get('tools', {}).items() if v]
        tools_missing = [k for k, v in caps.get('tools', {}).items() if not v]
        print('  Tools present: {0}'.format(', '.join(tools_present) if tools_present else 'none'))
        if tools_missing:
            print('  Tools missing: {0}'.format(', '.join(tools_missing)))
        print('  is_root: {0}'.format(caps.get('permissions',{}).get('is_root', False)))
        print('  can_write_cpufreq: {0}'.format(caps.get('permissions',{}).get('can_write_cpufreq', False)))
        
        # Print warnings
        warnings = self.info.get('warnings', [])
        if warnings:
            print('\nWARNINGS & RECOMMENDATIONS:')
            for i, w in enumerate(warnings, 1):
                print('  {0}. {1}'.format(i, w))
        
        print('-------------------------------------------')

    def to_json(self, path):
        try:
            with open(path, 'w') as fd:
                json.dump(self.info, fd, indent=2)
            return True
        except Exception as e:
            return False


if __name__ == '__main__':
    det = HardwareDetectorV2()
    det.print_report()
    # Save JSON next to script if desired
    try:
        outp = os.path.join(os.path.dirname(__file__), 'hardware_detect_report.json')
    except Exception:
        outp = 'hardware_detect_report.json'
    saved = det.to_json(outp)
    if saved:
        print('Saved JSON to', outp)
    else:
        print('Could not save JSON (permissions?)')
