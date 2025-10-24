# Proyecto 10 — Contexto para GitHub Copilot / Modelos de IA

## Resumen del proyecto

Ajuste Dinámico de Frecuencia (DVFS) en Sistemas Heterogéneos CPU–GPU mediante Aprendizaje Automático. Objetivo: diseñar e implementar un runtime ligero que, usando un modelo ML entrenado con métricas de ejecución, ajuste en tiempo real las frecuencias de CPU y GPU para minimizar el Energy–Delay Product (EDP) en aplicaciones HPC híbridas.

## Alcance y metas técnicas

- **Plataformas objetivo**: Cluster HPC UIS con CPUs Intel Xeon (múltiples arquitecturas: Nehalem, Westmere, Haswell) y GPUs NVIDIA (Tesla M2050, Tesla K20c, GTX TITAN X). Desarrollo local en Fedora con CPU Intel.
- **Hardware detection**: Script `detect_hardware_v2.py` (Python 2.7+/3.x compatible) para auditoría de hardware, capacidades de energía (RAPL/hwmon), y generación de JSON versionado (schema 2.0).
- **Workloads de referencia**: microbenchmarks CPU (dot product, memcpy), kernels GPU (small GEMM, stencil 3D, SpMV).
- **Objetivos entregables**: scripts de benchmarking y automatización; dataset CSV con 100 features diseñados; modelos ML entrenados (Random Forest, XGBoost); runtime (C++/Python) que aplique DVFS en línea; notebooks de análisis; manuscrito IMRAD.

## Estructura de archivos sugerida (repo)

```
/proyecto10/
├─ data/                  # datasets CSV ordenados por fecha
├─ benchmarks/
│  ├─ cpu/
│  │  ├─ dot.c
│  │  └─ memcpy.c
│  └─ gpu/
│     ├─ gemm.cu
│     └─ stencil.cu
├─ scripts/
│  ├─ run_benchmark.py    # automatiza cpufreq, ejecuciones y logs
│  ├─ measure_power.py    # wrapper para RAPL, NVML, intel_gpu_top
│  └─ generate_dataset.py
├─ runtime/
│  ├─ controller.py       # inferencia ML + aplicación de frecuencia
│  └─ controller.cpp      # alternativa en C++ o Rust
├─ models/
│  └─ rf_model.joblib
├─ notebooks/
│  └─ analysis.ipynb
└─ README.md
```

## Formato de dataset (CSV)

Campos sugeridos (columnas):
- timestamp (ISO8601)
- hostname
- cpu_model
- gpu_model
- kernel_name
- input_size
- freq_cpu_MHz
- freq_gpu_MHz
- time_s
- energy_J_cpu
- energy_J_gpu
- edp_Js
- instructions
- cycles
- ipc
- cache_misses
- l1_misses
- l2_misses
- sm_util_percent (si aplica)
- gpu_occupancy
- run_id

Unidades: frecuencias en MHz, tiempo en segundos, energía en Joules, EDP en Joules×segundos.

## APIs y herramientas (recomendadas)

- **CPU control**: `cpupower` / sysfs (`/sys/devices/system/cpu/cpu*/cpufreq/`)
- **CPU energy (Intel)**: RAPL (`turbostat`, `perf`, `pyRAPL`) or direct MSR via `msr-tools`
- **CPU energy (AMD)**: hwmon interface (`k10temp`, `zenpower`, `/sys/class/hwmon/`), AMD uProf para profiling avanzado
- **GPU control/medición (NVIDIA)**: `nvidia-smi`, `pynvml` (NVML API)
- **Perf profiling**: `perf stat` para ciclos, instrucciones, cache-misses, IPC, branch-misses
- **Hardware monitoring**: `/sys/class/hwmon/` para sensores de temperatura y potencia
- **Python libs**: `pynvml`, `psutil`, `pandas`, `scikit-learn`, `xgboost`, `joblib`, `optuna`, `numpy`, `matplotlib`, `seaborn`
- **Herramientas de cluster**: `numactl` (NUMA binding), `ipmitool` (BMC telemetry), `lshw`, `lspci`

## Hardware Detection (Script: detect_hardware_v2.py)

**Version:** 2.0 (Updated October 2025)

El script `detect_hardware_v2.py` es una utilidad **read-only** y **no-intrusiva** para detección completa de hardware en cluster HPC y estaciones de desarrollo:

**Características:**
- Compatible Python 2.7+ y 3.x (CentOS 7 y Fedora)
- Detección completa CPU/GPU/NUMA sin privilegios root
- Detección de capacidades de energía: RAPL (Intel), hwmon (AMD)
- **Detección avanzada AMD**: AMD uProf installation, version, MSR access, capabilities
- **GPU detection robusto**: nvidia-smi (primary) con lspci fallback para cluster con múltiples GPUs
- Detección de sensores hwmon (temperatura, potencia)
- Sistema de advertencias y recomendaciones automático con guías AMD-específicas
- Salida JSON versionada (schema v2.0) + reporte legible en consola
- **CLI arguments**: `--output-dir`, `--filename`, `--quiet`, `--json-only` para integración con SLURM/PBS

**Outputs:**
- `hardware_detect_report.json`: JSON estructurado con schema v2.0
- Reporte de consola con advertencias contextuales
- GPU indexing (0-7) para multi-GPU systems

**Documentación completa:**
- Ver `docs/HARDWARE_DETECTOR_SPEC.md` (especificación técnica completa)
- Ver `docs/AMD_PROFILING_GUIDE.md` (guía completa de profiling AMD)
- Ver `docs/DEPLOYMENT_GUIDE.md` (despliegue en cluster HPC)
- Ver `docs/ML_FEATURE_SET.md` (100 features para dataset ML)
- Ver `docs/cluster_capabilities.md` (resumen de nodos HPC disponibles)

**Cluster HPC UIS - Nodos disponibles:**
- **guane04**: 8× Tesla M2050 (2.6 GB), 24 CPUs, mejor para multi-GPU DVFS
- **thor**: 2× Tesla K20c (4.7 GB), 128 CPUs, RAPL disponible
- **felix**: 2× GTX TITAN X (12 GB), 64 CPUs, NUMA 4 nodos
- **yaje**: 1× GTX TITAN X (12 GB), 6 CPUs, single-socket test bed

**AMD-Specific Features:**
- Detecta instalación de AMD uProf (path, version, capabilities)
- Verifica disponibilidad de MSR para profiling avanzado
- Compara hwmon (k10temp/zenpower) vs AMD uProf capabilities
- Proporciona recomendaciones específicas por generación (Zen2/Zen3/Zen4)

## Pipeline de experimentos (alto nivel)

1. **Detección de hardware**: Usar `detect_hardware_v2.py` en cada nodo del cluster para auditar capacidades (CPU, GPU, RAPL, NUMA).
2. **Implementar y validar microbenchmarks** CPU/GPU con diferentes tamaños de entrada.
3. **Automatizar barridos de frecuencia**: Scripts que varíen frecuencias CPU (cpufreq) y GPU (nvidia-smi) en espacio discreto.
4. **Recolectar métricas completas**: 
   - Rendimiento: `perf stat` (IPC, cache-misses, branch-misses, stalls)
   - Energía: RAPL/hwmon (CPU), NVML (GPU)
   - Utilización: CPU/GPU utilization, temperatures, throttling
   - GPU profiling: occupancy, SM efficiency, memory bandwidth
5. **Generar dataset CSV**: 100 features por run (ver `docs/ML_FEATURE_SET.md`)
6. **Feature engineering**: Limpieza, normalización, interacciones, derivadas (notebook `analysis.ipynb`)
7. **Entrenamiento de modelos**: RF/XGBoost con validación k-fold, optimización hiperparámetros (Optuna)
8. **Implementar runtime**: Inferencia ligera + APIs de control de frecuencia en C++/Python
9. **Evaluación final**: Kernels de referencia (GEMM, stencil, SpMV), comparación estadística EDP
10. **Documentación**: Manuscrito IMRAD con resultados reproducibles

**Dataset objective**: 5000-10000 samples
- Frequency configs: 6 CPU × 6 GPU = 36 per workload
- Workloads: 5 kernels × 8 input sizes × 5 runs = 1440 base experiments

## Especificaciones para Copilot prompts (cómo pedirle ayuda)

- Mantener contexto: "Proyecto10: DVFS+ML; objetivo: minimizar EDP; dataset: columnas X; target: freq_cpu, freq_gpu".
- Pedir funciones unitarias: p.ej. "Escribe función Python que lea freq disponibles desde /sys/devices/... y devuelva lista de int MHz".
- Pedir tests: "Genera test pytest que verifique que run_benchmark.py produce un CSV con columnas esperadas".
- Pedir snippets de integración C++/Python: PyBind11 example para invocar Python ML model desde C++ runtime.

## Criterios de reproducibilidad y buenas prácticas

- Registrar commit SHA y versión del modelo en cada experimento.
- Incluir seed determinista en entrenamiento y experimentos aleatorios.
- Guardar metadatos del entorno (`lscpu`, `nvidia-smi -q`, `uname -a`) junto a cada dataset.
- Scripts con flags `--dry-run` y `--repeat N`.

## Notas de seguridad y permisos

- El proyecto requiere privilegios para cambiar frecuencias (`sudo cpupower`, `nvidia-smi -lgc`), documentar comandos exactos y pedir permiso de administrador en servidores.
- En cluster compartido, coordinar cambios de frecuencia con administrador y respetar políticas de uso.
- **Hardware detection es read-only**: No requiere privilegios, graceful degradation cuando RAPL/MSR no es accesible.
- Scripts de deployment: `scripts/deploy_to_cluster.sh` automatiza transferencia y validación en nodos remotos.
- Git workflow: Conventional commits (feat/fix/docs/chore) con mensajes detallados.

---

## Progreso actual del proyecto (October 2025)

### ✅ Completado
- [x] Hardware detection v2.0 con soporte AMD completo, GPU multi-device, CLI arguments
- [x] Test suite comprehensivo (23 tests passing)
- [x] Documentación técnica (1300+ líneas): HARDWARE_DETECTOR_SPEC, AMD_PROFILING_GUIDE, DEPLOYMENT_GUIDE
- [x] Feature set para ML: 100 features definidos con rationale y estrategia de colección
- [x] Caracterización de nodos del cluster HPC UIS (4 nodos documentados)
- [x] Scripts de deployment automatizado para cluster

### 🔄 En progreso
- [ ] Implementación de microbenchmarks CPU/GPU
- [ ] Scripts de automatización de experimentos (run_benchmark.py)
- [ ] Colección de dataset inicial (MVP: 1000 samples)
- [ ] Análisis exploratorio de datos

### 📋 Pendiente
- [ ] Entrenamiento de modelos iniciales (RF/XGBoost)
- [ ] Runtime de inferencia y control DVFS
- [ ] Evaluación en kernels de referencia
- [ ] Manuscrito IMRAD

---

*Este archivo sirve como punto de partida para prompts a Copilot y otros modelos de IA. Mantenerlo actualizado conforme evolucionen las pruebas y el entorno experimental.*

