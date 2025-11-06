# Frequency Sweep Automation

Script para automatizar la recolección de métricas de rendimiento y energía en diferentes combinaciones de frecuencias CPU/GPU para el entrenamiento de modelos ML de DVFS.

## Características

✅ **Compatible Python 2.7+ y 3.x** (CentOS 7 y Fedora)  
✅ **Control de frecuencias CPU** (cpupower o sysfs)  
✅ **Control de frecuencias GPU** (nvidia-smi)  
✅ **Instrumentación con perf** (IPC, cache misses, instructions, cycles)  
✅ **Medición de energía** (RAPL para CPU, NVML para GPU)  
✅ **Cálculo automático de EDP** (Energy-Delay Product)  
✅ **Salida CSV** lista para pandas y ML  
✅ **Manejo robusto de errores** (timeouts, permisos, hardware faltante)

## Uso Básico

### 1. Preparar configuración

Editar `configs/sweep_config_example.json`:

```json
{
  "cpu_frequencies": [1200, 1600, 2000, 2400],
  "gpu_frequencies": [500, 700, 900, 1100],
  "benchmarks": [
    {
      "name": "dot_product",
      "cmd": "./benchmarks/cpu/dot {input_size}"
    }
  ],
  "input_sizes": [1000000, 10000000],
  "repetitions": 5,
  "output_file": "data/sweep_results.csv"
}
```

### 2. Verificar permisos (IMPORTANTE)

El script necesita **sudo** para cambiar frecuencias:

```bash
# Verificar cpupower
sudo cpupower frequency-info

# Verificar nvidia-smi
sudo nvidia-smi -i 0 -pm 1
sudo nvidia-smi -i 0 -lgc 1000  # Test setting GPU clock
```

**Nota:** En cluster compartido, coordinar con administrador antes de ejecutar.

### 3. Ejecutar en modo dry-run (recomendado)

```bash
python scripts/run_sweep.py -c configs/sweep_config_example.json --dry-run
```

Esto imprime la configuración sin ejecutar experimentos.

### 4. Ejecutar barrido completo

```bash
python scripts/run_sweep.py -c configs/my_sweep.json
```

## Formato de Salida (CSV)

El script genera un CSV con las siguientes columnas:

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `timestamp` | datetime | Fecha/hora UTC (ISO8601) |
| `run_id` | string | ID único (run_000001, run_000002, ...) |
| `hostname` | string | Nodo del cluster |
| `cpu_model` | string | Modelo de CPU |
| `gpu_model` | string | Modelo de GPU |
| `kernel_name` | string | Nombre del benchmark |
| `input_size` | int | Tamaño del problema |
| `freq_cpu_MHz` | int | Frecuencia CPU configurada (MHz) |
| `freq_gpu_MHz` | int | Frecuencia GPU configurada (MHz) |
| `time_s` | float | Tiempo de ejecución (segundos) |
| `energy_J_cpu` | float | Energía CPU (Joules) |
| `energy_J_gpu` | float | Energía GPU (Joules) |
| `edp_Js` | float | Energy-Delay Product (J·s) |
| `instructions` | int | Instrucciones ejecutadas (perf) |
| `cycles` | int | Ciclos consumidos (perf) |
| `ipc` | float | Instructions per cycle |
| `cache_misses` | int | Total cache misses |
| `l1_misses` | int | L1 dcache load misses |
| `l2_misses` | int | LLC load misses |
| `sm_util_percent` | float | GPU SM utilization (%) |
| `gpu_occupancy` | float | GPU occupancy (%) |

## Ejemplo de Configuración para guane04

```json
{
  "description": "Multi-GPU sweep on guane04 (8x Tesla M2050)",
  "cpu_frequencies": [1600, 2000, 2400],
  "gpu_frequencies": [500, 700, 900, 1100],
  "benchmarks": [
    {
      "name": "dot_cpu",
      "cmd": "./benchmarks/cpu/dot {input_size}"
    },
    {
      "name": "gemm_gpu",
      "cmd": "CUDA_VISIBLE_DEVICES=0 ./benchmarks/gpu/gemm {input_size}"
    }
  ],
  "input_sizes": [1000000, 10000000, 50000000],
  "repetitions": 5,
  "output_file": "data/guane04_sweep.csv"
}
```

**Estimación de tiempo:**
- 3 CPU freqs × 4 GPU freqs × 2 benchmarks × 3 sizes × 5 reps = **360 experimentos**
- ~10 segundos por experimento = **~60 minutos**

## Limitaciones y TODOs

### Actualmente Implementado
- ✅ Control de frecuencias CPU/GPU
- ✅ Perf instrumentation (IPC, cache misses)
- ✅ RAPL energy (CPU)
- ✅ Timeouts y manejo de errores
- ✅ CSV output

### Pendiente (PRs bienvenidos!)
- ⚠️ **NVML integration**: Energía GPU por integración directa (actualmente None)
- ⚠️ **GPU metrics**: SM utilization, occupancy (requiere CUPTI o nvprof)
- ⚠️ **Temperaturas**: CPU/GPU temperature monitoring
- ⚠️ **Memory bandwidth**: Medición de ancho de banda usado
- ⚠️ **NUMA awareness**: Binding a nodos NUMA específicos

## Troubleshooting

### Error: "cpupower failed (permissions?)"

**Solución:** Ejecutar con sudo o configurar permisos:

```bash
# Temporal (requiere sudo cada vez)
sudo python scripts/run_sweep.py -c config.json

# Permanente (peligroso en cluster compartido!)
sudo chmod u+s $(which cpupower)  # NO RECOMENDADO
```

### Error: "RAPL not accessible"

**Causa:** RAPL requiere permisos de lectura en `/sys/class/powercap/`

**Solución:**
```bash
# Verificar
ls -l /sys/class/powercap/intel-rapl:0/energy_uj

# Solicitar al admin agregar regla udev:
# /etc/udev/rules.d/99-rapl.rules
# SUBSYSTEM=="powercap", RUN+="/bin/chmod 0444 $env{DEVPATH}/energy_uj"
```

**Workaround:** El script continúa sin RAPL, pero `energy_J_cpu` será `None`.

### Error: "nvidia-smi: command not found"

**Causa:** Drivers NVIDIA no instalados o no en PATH.

**Solución:**
```bash
# Verificar instalación
which nvidia-smi
/usr/bin/nvidia-smi --version

# Si no está, pedir al admin instalar drivers
```

### Benchmark timeout

**Causa:** Benchmark tarda >5 minutos (timeout por defecto).

**Solución:** Editar `run_sweep.py` línea ~340:
```python
timeout=300  # cambiar a 600 (10 minutos) o más
```

## Integración con SLURM

Para ejecutar en cluster con SLURM:

```bash
#!/bin/bash
#SBATCH --job-name=dvfs_sweep
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00
#SBATCH --output=logs/sweep_%j.out

module load python/3.8
module load cuda/11.0

python scripts/run_sweep.py -c configs/sweep_config.json
```

## Referencias

- [Linux perf documentation](https://perf.wiki.kernel.org/)
- [NVIDIA NVML API](https://developer.nvidia.com/nvidia-management-library-nvml)
- [Intel RAPL interface](https://www.kernel.org/doc/html/latest/power/powercap/powercap.html)
- [cpufreq governors](https://www.kernel.org/doc/Documentation/cpu-freq/governors.txt)

## Contribuir

Para añadir nuevas métricas o benchmarks:

1. Editar `run_benchmark_with_perf()` para nuevas métricas
2. Actualizar `fieldnames` en `run_sweep()` para nuevas columnas CSV
3. Añadir tests en `tests/test_run_sweep.py`
4. Crear PR con descripción detallada

---

**Mantenido por:** Proyecto 10 - DVFS+ML  
**Última actualización:** Noviembre 2025
