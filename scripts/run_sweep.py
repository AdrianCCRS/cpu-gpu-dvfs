#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frequency Sweep Automation for DVFS+ML Dataset Generation
Proyecto 10 - HPC DVFS via Machine Learning

This script automates the collection of performance and energy metrics
across different CPU/GPU frequency combinations for training ML models.

Requires: Python 3.9+
"""

import os
import sys
import time
import json
import argparse
import subprocess
import csv
from pathlib import Path
from shutil import which
from datetime import datetime
from typing import Dict, List, Optional, Any


class FrequencySweep:
    """
    Orchestrates frequency sweep experiments across CPU/GPU benchmarks.
    
    Responsibilities:
    1. Set CPU/GPU frequencies
    2. Execute benchmarks with perf instrumentation
    3. Collect energy metrics (RAPL, NVML)
    4. Parse performance counters
    5. Write results to CSV
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize sweep controller.
        
        Args:
            config: Dictionary with experiment configuration
        """
        self.config = config
        self.hostname = self._get_hostname()
        self.cpu_model = self._get_cpu_model()
        self.gpu_model = self._get_gpu_model()
        self.output_file = config.get('output_file', 'dataset.csv')
        self.perf_available = which('perf') is not None
        self.nvidia_smi_available = which('nvidia-smi') is not None
        
        # Check capabilities
        self._check_capabilities()
    
    def _get_hostname(self) -> str:
        """Get system hostname"""
        try:
            import socket
            return socket.gethostname()
        except Exception:
            return 'unknown'
    
    def _get_cpu_model(self) -> str:
        """Extract CPU model from /proc/cpuinfo"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'model name' in line:
                        return line.split(':')[1].strip()
        except Exception:
            pass
        return 'unknown'
    
    def _get_gpu_model(self) -> str:
        """Get GPU model via nvidia-smi"""
        if not self.nvidia_smi_available:
            return 'none'
        
        try:
            cmd = ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader', '-i', '0']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except Exception:
            return 'none'
    
    def _check_capabilities(self) -> None:
        """Check what monitoring tools are available"""
        print("=== Checking System Capabilities ===")
        print(f"Hostname: {self.hostname}")
        print(f"CPU: {self.cpu_model}")
        print(f"GPU: {self.gpu_model}")
        print(f"perf: {'available' if self.perf_available else 'NOT FOUND'}")
        print(f"nvidia-smi: {'available' if self.nvidia_smi_available else 'NOT FOUND'}")
        
        # Check RAPL
        rapl_path = Path('/sys/class/powercap/intel-rapl:0/energy_uj')
        rapl_readable = rapl_path.is_file() and os.access(rapl_path, os.R_OK)
        print(f"RAPL: {'readable' if rapl_readable else 'NOT ACCESSIBLE'}")
        
        if not self.perf_available:
            print("WARNING: perf not available. CPU metrics will be limited.")
        if not self.nvidia_smi_available:
            print("WARNING: nvidia-smi not available. GPU metrics will be limited.")
        print()
    
    def set_cpu_frequency(self, freq_mhz: int) -> bool:
        """
        Set CPU frequency using cpupower or sysfs.
        
        Args:
            freq_mhz: Target frequency in MHz
            
        Returns:
            True if successful
        """
        freq_khz = freq_mhz * 1000
        
        # Method 1: Try cpupower (requires sudo)
        if which('cpupower'):
            try:
                # Set governor to userspace
                subprocess.run(
                    ['sudo', 'cpupower', 'frequency-set', '-g', 'userspace'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                # Set frequency
                subprocess.run(
                    ['sudo', 'cpupower', 'frequency-set', '-f', f'{freq_khz}kHz'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                print(f"CPU frequency set to {freq_mhz} MHz (cpupower)")
                return True
            except subprocess.CalledProcessError:
                print("WARNING: cpupower failed (permissions?)")
        
        # Method 2: Try sysfs directly (also needs permissions)
        try:
            cpu_dirs = [d for d in os.listdir('/sys/devices/system/cpu') 
                       if d.startswith('cpu') and d[3:].isdigit()]
            
            for cpu_dir in cpu_dirs:
                scaling_setspeed = Path(f'/sys/devices/system/cpu/{cpu_dir}/cpufreq/scaling_setspeed')
                if scaling_setspeed.is_file():
                    scaling_setspeed.write_text(str(freq_khz))
            
            print(f"CPU frequency set to {freq_mhz} MHz (sysfs)")
            return True
        except (IOError, OSError) as e:
            print(f"WARNING: Cannot set CPU frequency: {e}")
            print("Continuing with current frequency...")
            return False
    
    def set_gpu_frequency(self, freq_mhz: int, gpu_id: int = 0) -> bool:
        """
        Set GPU frequency using nvidia-smi.
        
        Args:
            freq_mhz: Target frequency in MHz
            gpu_id: GPU index (0-7)
            
        Returns:
            True if successful
        """
        if not self.nvidia_smi_available:
            print("WARNING: nvidia-smi not available, cannot set GPU frequency")
            return False
        
        try:
            # Unlock frequency control
            subprocess.run(
                ['sudo', 'nvidia-smi', '-i', str(gpu_id), '-pm', '1'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            
            # Set graphics clock
            subprocess.run(
                ['sudo', 'nvidia-smi', '-i', str(gpu_id), '-lgc', str(freq_mhz)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            
            print(f"GPU {gpu_id} frequency set to {freq_mhz} MHz")
            return True
        except subprocess.CalledProcessError as e:
            print(f"WARNING: Cannot set GPU frequency: {e}")
            print("Continuing with current frequency...")
            return False
    
    def read_rapl_energy(self) -> Optional[int]:
        """
        Read CPU package energy from RAPL.
        
        Returns:
            Energy in microjoules, or None if unavailable
        """
        rapl_path = Path('/sys/class/powercap/intel-rapl:0/energy_uj')
        try:
            return int(rapl_path.read_text().strip())
        except (IOError, OSError, ValueError):
            return None
    
    def get_gpu_power(self, gpu_id: int = 0) -> Optional[float]:
        """
        Get current GPU power draw via nvidia-smi.
        
        Args:
            gpu_id: GPU index
            
        Returns:
            Power in watts, or None if unavailable
        """
        if not self.nvidia_smi_available:
            return None
        
        try:
            cmd = ['nvidia-smi', '--query-gpu=power.draw', 
                   '--format=csv,noheader,nounits', '-i', str(gpu_id)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return None
    
    def run_benchmark_with_perf(self, benchmark_cmd: List[str], 
                                kernel_name: str, input_size: int) -> Optional[Dict[str, Any]]:
        """
        Execute benchmark with perf instrumentation.
        
        Args:
            benchmark_cmd: Command arguments list
            kernel_name: Name of the kernel
            input_size: Problem size
            
        Returns:
            Dictionary with collected metrics, or None if failed
        """
        metrics = {
            'kernel_name': kernel_name,
            'input_size': input_size,
            'hostname': self.hostname,
            'cpu_model': self.cpu_model,
            'gpu_model': self.gpu_model,
            'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        
        # Prepare perf command if available
        if self.perf_available:
            perf_events = [
                'instructions',
                'cycles',
                'cache-misses',
                'L1-dcache-load-misses',
                'LLC-load-misses',
            ]
            perf_cmd = ['perf', 'stat', '-e', ','.join(perf_events)] + benchmark_cmd
        else:
            perf_cmd = benchmark_cmd
        
        print(f"  Running: {' '.join(benchmark_cmd)}")
        
        # Read energy before
        energy_start_cpu = self.read_rapl_energy()
        time_start = time.time()
        
        # Execute benchmark
        try:
            result = subprocess.run(
                perf_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,  # 5 minute timeout
                text=True
            )
            
            time_end = time.time()
            energy_end_cpu = self.read_rapl_energy()
            
            # Calculate metrics
            metrics['time_s'] = time_end - time_start
            
            # CPU energy
            if energy_start_cpu is not None and energy_end_cpu is not None:
                energy_uj = energy_end_cpu - energy_start_cpu
                # Handle counter wraparound
                if energy_uj < 0:
                    energy_uj += 2**32
                metrics['energy_J_cpu'] = energy_uj / 1e6
            else:
                metrics['energy_J_cpu'] = None
            
            # Parse perf output
            if self.perf_available:
                perf_output = result.stderr
                metrics.update(self._parse_perf_output(perf_output))
            
            # GPU metrics (placeholder - will need NVML integration)
            metrics['energy_J_gpu'] = None  # TODO: integrate NVML
            metrics['sm_util_percent'] = None
            metrics['gpu_occupancy'] = None
            
            # Calculate EDP
            if metrics['energy_J_cpu'] is not None:
                total_energy = metrics['energy_J_cpu']
                if metrics['energy_J_gpu'] is not None:
                    total_energy += metrics['energy_J_gpu']
                metrics['edp_Js'] = total_energy * metrics['time_s']
            else:
                metrics['edp_Js'] = None
            
            print(f"  Completed in {metrics['time_s']:.3f}s")
            
        except subprocess.TimeoutExpired:
            print("  ERROR: Benchmark timed out")
            return None
        except Exception as e:
            print(f"  ERROR: {e}")
            return None
        
        return metrics
    
    def _parse_perf_output(self, perf_output: str) -> Dict[str, Any]:
        """
        Parse perf stat output to extract counters.
        
        Args:
            perf_output: stderr from perf stat
            
        Returns:
            Dictionary with parsed metrics
        """
        metrics = {
            'instructions': None,
            'cycles': None,
            'ipc': None,
            'cache_misses': None,
            'l1_misses': None,
            'l2_misses': None,
        }
        
        for line in perf_output.split('\n'):
            line = line.strip()
            
            # Parse format: "1,234,567 instructions"
            if 'instructions' in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        metrics['instructions'] = int(parts[0].replace(',', ''))
                    except ValueError:
                        pass
            
            elif 'cycles' in line and 'stalled' not in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        metrics['cycles'] = int(parts[0].replace(',', ''))
                    except ValueError:
                        pass
            
            elif 'cache-misses' in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        metrics['cache_misses'] = int(parts[0].replace(',', ''))
                    except ValueError:
                        pass
            
            elif 'L1-dcache-load-misses' in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        metrics['l1_misses'] = int(parts[0].replace(',', ''))
                    except ValueError:
                        pass
            
            elif 'LLC-load-misses' in line:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        metrics['l2_misses'] = int(parts[0].replace(',', ''))
                    except ValueError:
                        pass
        
        # Calculate IPC
        if metrics['instructions'] and metrics['cycles']:
            metrics['ipc'] = float(metrics['instructions']) / float(metrics['cycles'])
        
        return metrics
    
    def run_sweep(self) -> None:
        """
        Main sweep orchestration.
        
        Iterates through:
        - CPU frequencies
        - GPU frequencies
        - Benchmarks
        - Input sizes
        - Repetitions
        """
        cpu_freqs = self.config.get('cpu_frequencies', [])
        gpu_freqs = self.config.get('gpu_frequencies', [])
        benchmarks = self.config.get('benchmarks', [])
        input_sizes = self.config.get('input_sizes', [])
        repetitions = self.config.get('repetitions', 5)
        
        print("=== Starting Frequency Sweep ===")
        print(f"CPU frequencies: {cpu_freqs}")
        print(f"GPU frequencies: {gpu_freqs}")
        print(f"Benchmarks: {[b['name'] for b in benchmarks]}")
        print(f"Input sizes: {input_sizes}")
        print(f"Repetitions: {repetitions}")
        print()
        
        # Initialize CSV
        csv_file = open(self.output_file, 'w', newline='')
        fieldnames = [
            'timestamp', 'run_id', 'hostname', 'cpu_model', 'gpu_model',
            'kernel_name', 'input_size', 'freq_cpu_MHz', 'freq_gpu_MHz',
            'time_s', 'energy_J_cpu', 'energy_J_gpu', 'edp_Js',
            'instructions', 'cycles', 'ipc',
            'cache_misses', 'l1_misses', 'l2_misses',
            'sm_util_percent', 'gpu_occupancy'
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        
        run_id = 0
        total_runs = len(cpu_freqs) * len(gpu_freqs) * len(benchmarks) * len(input_sizes) * repetitions
        
        try:
            for cpu_freq in cpu_freqs:
                self.set_cpu_frequency(cpu_freq)
                
                for gpu_freq in gpu_freqs:
                    self.set_gpu_frequency(gpu_freq)
                    
                    # Allow frequencies to stabilize
                    time.sleep(2)
                    
                    for benchmark in benchmarks:
                        for input_size in input_sizes:
                            for rep in range(repetitions):
                                run_id += 1
                                print(f"[{run_id}/{total_runs}] CPU={cpu_freq} MHz, GPU={gpu_freq} MHz, "
                                      f"{benchmark['name']}, size={input_size}, rep={rep + 1}")
                                
                                # Build benchmark command
                                cmd = benchmark['cmd'].format(input_size=input_size)
                                cmd_list = cmd.split()
                                
                                # Run benchmark
                                metrics = self.run_benchmark_with_perf(
                                    cmd_list,
                                    benchmark['name'],
                                    input_size
                                )
                                
                                if metrics:
                                    metrics['run_id'] = f'run_{run_id:06d}'
                                    metrics['freq_cpu_MHz'] = cpu_freq
                                    metrics['freq_gpu_MHz'] = gpu_freq
                                    
                                    # Write to CSV
                                    writer.writerow(metrics)
                                    csv_file.flush()
                                
                                # Small delay between runs
                                time.sleep(1)
        
        finally:
            csv_file.close()
            print("\n=== Sweep Complete ===")
            print(f"Results saved to: {self.output_file}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Automated frequency sweep for DVFS+ML dataset generation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Example configuration file (sweep_config.json):
{
  "cpu_frequencies": [1200, 1600, 2000, 2400],
  "gpu_frequencies": [500, 700, 900, 1100],
  "benchmarks": [
    {
      "name": "dot_product",
      "cmd": "./benchmarks/cpu/dot {input_size}"
    }
  ],
  "input_sizes": [1000000, 10000000, 100000000],
  "repetitions": 5,
  "output_file": "data/sweep_results.csv"
}
        '''
    )
    
    parser.add_argument(
        '-c', '--config',
        type=str,
        required=True,
        help='Path to JSON configuration file'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print configuration without running experiments'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"ERROR: Cannot load config file: {e}")
        return 1
    
    if args.dry_run:
        print("=== DRY RUN MODE ===")
        print(json.dumps(config, indent=2))
        return 0
    
    # Run sweep
    sweep = FrequencySweep(config)
    sweep.run_sweep()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
