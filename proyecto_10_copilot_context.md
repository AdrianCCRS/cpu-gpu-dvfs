# Proyecto 10 — Contexto para GitHub Copilot / Modelos de IA

## Resumen del proyecto

Ajuste Dinámico de Frecuencia (DVFS) en Sistemas Heterogéneos CPU–GPU mediante Aprendizaje Automático. Objetivo: diseñar e implementar un runtime ligero que, usando un modelo ML entrenado con métricas de ejecución, ajuste en tiempo real las frecuencias de CPU y GPU para minimizar el Energy–Delay Product (EDP) en aplicaciones HPC híbridas.

## Alcance y metas técnicas

- Plataformas iniciales: CPU Intel (RAPL, cpufreq) y GPU Intel (Iris Xe) en entorno local; validación posterior en servidor HPC con GPUs NVIDIA (NVML).
- Workloads de referencia: microbenchmarks CPU (dot product, memcpy), kernels GPU (small GEMM, stencil 3D, SpMV).
- Objetivos entregables: scripts de benchmarking y automatización; dataset CSV; modelos ML entrenados (Random Forest, XGBoost); runtime (C++/Python) que aplique DVFS en línea; notebooks de análisis; manuscrito IMRAD.

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

- CPU control: `cpupower` / sysfs (`/sys/devices/system/cpu/cpu*/cpufreq/`)
- CPU energy: RAPL (`turbostat`, `perf`, `pyRAPL`) or direct MSR via `msr-tools`
- GPU control/medición (NVIDIA): `nvidia-smi`, `pynvml`
- Intel GPU (local): `intel_gpu_top`, `intel_gpu_frequency` (si disponible), `IGT` tools
- Perf profiling: `perf stat` para ciclos, instrucciones, cache-misses
- Python libs: `pynvml`, `psutil`, `pandas`, `scikit-learn`, `xgboost`, `joblib`, `optuna`

## Pipeline de experimentos (alto nivel)

1. Identificar hardware y capacidades (scripts `detect_hardware.sh`).
2. Implementar y validar microbenchmarks CPU/GPU.
3. Automatizar barridos de frecuencia (espacio discreto) y tamaños de entrada.
4. Recolectar métricas con `perf`, RAPL/NVML y guardar CSVs.
5. Limpieza y feature engineering (notebook `analysis.ipynb`).
6. Entrenamiento de modelos (RF/XGBoost) y validación (k-fold).
7. Implementar runtime: inferencia ligera + APIs de control de frecuencia.
8. Evaluación final en kernels de referencia y comparación estadística.

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

- El proyecto requiere privilegios para cambiar frecuencias (`sudo cpupower`), documentar comandos exactos y pedir permiso de administrador en servidores.
- En servidores compartidos, coordinar cambios de frecuencia con el administrador y respetar políticas de uso.

---

*Este archivo sirve como punto de partida para prompts a Copilot y otros modelos de IA. Mantenerlo actualizado conforme evolucionen las pruebas y el entorno experimental.*

