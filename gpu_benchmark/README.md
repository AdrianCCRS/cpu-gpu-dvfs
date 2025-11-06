# GPU GEMM Microbenchmark (CUDA)

Este microbenchmark proporciona dos maneras de ejecutar el kernel GEMM (naive) y recoger métricas GPU:

- Versión simple (binario `gemm_benchmark`) — mide con CUDA events y escribe una línea parseable.
- Versión Google Benchmark (binario `gemm_benchmark_google`) — usa Google Benchmark para controlar repeticiones/iteraciones y produce JSON más rico.

Contenido
- `CMakeLists.txt` — Proyecto CMake que compila `gemm_benchmark` y (si está disponible) `gemm_benchmark_google`.
- `gemm_benchmark.cu` — Kernel `gemm_naive` y versión simple que mide con CUDA events.
- `gemm_benchmark_google.cu` — Versión que integra Google Benchmark y reporta counters (se compila si `benchmark` está presente).
- `run_gpu_benchmark.sh` — Script que compila, ejecuta los benchmarks, muestrea `nvidia-smi` y genera `results_gpu.csv`.

Resumen de las implementaciones
------------------------------
- `gemm_benchmark.cu` — Implementación CUDA "naive" del kernel GEMM. Mide tiempo por iteración con eventos CUDA y sirve como binario sencillo de referencia.
- `gemm_benchmark_google.cu` — Misma operación medida con Google Benchmark (cuando la biblioteca está disponible). Emplea UseManualTime() para cronometrar la ejecución en GPU y publica contadores opcionales (por ejemplo GFLOPS calculadas).
- `gpu_monitor_nvml.cpp` — Utilidad C++ que usa NVML para muestrear potencia, relojes, utilización y temperatura mientras el benchmark corre. Se lanza como proceso padre y ejecuta el benchmark como hijo.
- `run_gpu_benchmark.sh` — Orquestador: detecta nvcc, compila, ejecuta cada tamaño de problema, invoca el monitor NVML (si está disponible) y genera un CSV con las métricas agregadas.

Dependencias y qué usa cada componente
---------------------------------------
- nvcc / CUDA Toolkit: compila los `.cu`.
- Google Benchmark (opcional): si está presente en el sistema, CMake construye `gemm_benchmark_google`.
- NVML (libnvidia-ml): el monitor C++ (`gpu_monitor_nvml`) usa la API NVML. Si NVML no está presente, el monitor no se construirá.
- nvidia-smi: históricamente usado para muestreo; el runner ahora prefiere NVML cuando está disponible.
- Python: el runner usa una pequeña porción de Python para parsear JSON de Google Benchmark (si corresponde).

Métricas recogidas y columnas del CSV
------------------------------------
El CSV generado (`results_gpu.csv`) contiene únicamente métricas relacionadas con GPU. Columnas y su significado:

- timestamp: marca de tiempo ISO de la ejecución.
- kernel_name: nombre del kernel/benchmark ejecutado (p.ej. `gemm_naive`).
- problem_size: tamaño MxKxN del GEMM medido.
- iterations: iteraciones solicitadas (valor del script o bandera del benchmark).
- gpu_core_clock_MHz: reloj promedio del núcleo GPU durante la ejecución (MHz).
- gpu_mem_clock_MHz: reloj promedio de memoria (MHz).
- gpu_utilization_pct: utilización media de la GPU (%) reportada por NVML.
- occupancy: ocupación teórica (si el benchmark publica este contador; 0 si no disponible).
- throughput_gflops: GFLOPS reportados por el benchmark (si está disponible) o 0.
- bandwidth_gbps: estimación del ancho de banda efectivo (GB/s) calculada como (bytes movidos / tiempo).
- power_avg_w: potencia media medida (W).
- energy_j: energía estimada consumida durante la ejecución (J) = power_avg_w * duration_s.
- edp: Energy-Delay Product (E * t).
- gflops_per_watt: eficiencia energética (GFLOPS/W).
- gpu_temp_c: temperatura media (°C).
- ed2p: E * t^2 (otra métrica compuesta).

Ejecución (resumen)
-------------------
1. Compilar y ejecutar todo automáticamente:

```bash
cd benchmark/gpu_benchmark
chmod +x run_gpu_benchmark.sh
./run_gpu_benchmark.sh
```

2. Qué hace el script:
- Detecta `nvcc` y corre `cmake`/`make` en `build/`.
- Si `gpu_monitor_nvml` fue construido (NVML disponible), lo usa para muestrear durante cada corrida.
- Si `gemm_benchmark_google` existe, ejecuta la versión Google Benchmark (salida JSON) y extrae agregados.
- Genera un único archivo `results_gpu.csv` con una fila por problema/talla y no deja archivos temporales en el repo (usa y borra archivos temporales en un directorio temporal por ejecución).

Limpieza y archivos temporales
------------------------------
- El runner ya no deja ficheros intermedios persistentes (p.ej. `gbout.json`, `gb_parsed.tmp`, ni `gpu_samples.tmp`). Usa un directorio temporal (mktemp -d) y lo borra al finalizar. El único artefacto permanente es `results_gpu.csv`.
- Hice una pasada de saneamiento para eliminar archivos temporales residuales del directorio `benchmark/gpu_benchmark`.

Problemas conocidos y recomendaciones
------------------------------------
- En algunos sistemas `nvidia-smi` o NVML pueden reportar 0s para algunos campos dependiendo del driver y la GPU — para lecturas más profundas considera Nsight/NVProf o APIs específicas del proveedor.
- Si la extensión de C/C++ de VS Code muestra errores sobre `nvml.h`, asegúrate de que la ruta `/usr/local/cuda-*/include` esté en el includePath (he añadido `.vscode/c_cpp_properties.json` en la raíz y en el subfolder para facilitar esto).

Contribuciones y mejoras posibles
---------------------------------
- Añadir un monitor en Python (pynvml) como fallback si no quieres compilar C++.
- Integrar Nsight para counters por kernel.
- Añadir forwarding de flags desde `run_gpu_benchmark.sh` a `gemm_benchmark_google`.

Objetivo
- Proveer una herramienta mínima y reproducible para medir rendimiento GPU (GFLOPS), utilización, relojes, energía y métricas derivadas como EDP. El script combina las mediciones del binario con muestreo `nvidia-smi` para obtener promedios de potencia/uso/relojes.

CSV generado (columnas relevantes para GPU)
- timestamp,kernel_name,problem_size,iterations,gpu_core_clock_MHz,gpu_mem_clock_MHz,gpu_utilization_pct,occupancy,throughput_gflops,bandwidth_gbps,power_avg_w,energy_j,edp,gflops_per_watt,gpu_temp_c,ed2p

Notas importantes
- El CSV está centrado en métricas GPU; no contiene columnas de contadores de CPU ni métricas que no aplican al kernel GPU.
- `nvidia-smi` se usa para muestrear `power.draw`, `utilization.gpu`, `clocks.gr`, `clocks.mem` y `temperature.gpu`. Asegúrate de tener drivers NVIDIA y `nvidia-smi` disponible.

Modo de uso rápido
1. Asegúrate de tener CUDA Toolkit (nvcc) y drivers NVIDIA.
2. Ejecuta el script (compila y corre automáticamente):

```bash
cd gpu_benchmark
chmod +x run_gpu_benchmark.sh
./run_gpu_benchmark.sh
```

Ejecución en servidor (headless) — paso a paso
--------------------------------------------
Si vas a ejecutar el benchmark en un servidor (sin entorno gráfico), sigue estos pasos mínimos y reproducibles.

1) Prerrequisitos (instala/valida en el servidor):

- Drivers NVIDIA instalados y `nvidia-smi` disponible.
- CUDA Toolkit (nvcc) disponible si quieres compilar los .cu (recomendado). Verifica con `which nvcc`.
- (`opcional`) Headers y librería NVML (`nvml.h` y `libnvidia-ml.so`) si quieres usar el monitor C++ (se suelen instalar con el driver/CUDA). Verifica:

```bash
find /usr/local/cuda-*/include -name nvml.h || true
ls -l /usr/lib64/libnvidia-ml.so || true
which nvcc || true
nvidia-smi --query-gpu=name,driver_version --format=csv
```

2) Clona el repo y ve al subdirectorio del benchmark:

```bash
git clone <repo-url> && cd Microbrencmark/benchmark/gpu_benchmark
```

3) Compilar (en modo no interactivo):

```bash
mkdir -p build && cd build
cmake .. -DCMAKE_CUDA_COMPILER=$(command -v nvcc)
make -j $(nproc)
cd ..
```

4) Ejecutar el runner en background (opciones):

- Usando `nohup` (simple):

```bash
nohup ./run_gpu_benchmark.sh > run_bench.log 2>&1 &
echo $! > run_bench.pid
tail -f run_bench.log
```

- Usando `tmux` o `screen` (recomendado para control interactivo):

```bash
tmux new -s gpu_bench
# dentro de tmux
./run_gpu_benchmark.sh
# luego detach con Ctrl-B D
```

- Como servicio systemd (para ejecuciones repetidas/autostart) — ejemplo mínimo:

```ini
[Unit]
Description=GPU GEMM Benchmark
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/Microbrencmark/benchmark/gpu_benchmark
ExecStart=/path/to/Microbrencmark/benchmark/gpu_benchmark/run_gpu_benchmark.sh
Restart=no

[Install]
WantedBy=multi-user.target
```

5) Verificar resultados

- El runner escribe `results_gpu.csv` en el directorio `benchmark/gpu_benchmark`.
- Comprueba el archivo y los últimos timestamps:

```bash
ls -l results_gpu.csv
head -n 5 results_gpu.csv
```

6) Logs y troubleshooting

- El log del proceso (stdout/stderr) estará en `run_bench.log` si usaste `nohup`, o en la sesión `tmux` si usaste `tmux`.
- Si el monitor NVML no está disponible, el script dejará un mensaje indicando que no se ha construido `gpu_monitor_nvml` — en ese caso el runner fallará o puedes optar por instalar NVML headers/libs, o usar el fallback `nvidia-smi` (pídemelo y lo configuro).

7) Configuración rápida para ejecuciones largas

- Aumenta `ITERATIONS` y/o los tamaños en la variable `SIZES` en `run_gpu_benchmark.sh`.
- Si necesitas controlar Google Benchmark flags desde el script (p.ej. `--benchmark_repetitions`), puedo añadir forwarding para pasar flags al binario desde `run_gpu_benchmark.sh`.

8) Seguridad y permisos

- Ejecuta como usuario no-root cuando sea posible (requiere que el usuario tenga acceso a los dispositivos `/dev/nvidia*`).
- Si usas `sudo` para instalar paquetes o compilar, vuelve al usuario normal para ejecutar los benchmarks.


Uso con NVML (monitor C++ integrado)
----------------------------------
Este repositorio incluye un monitor NVML (`gpu_monitor_nvml`) para muestrear potencia, relojes, utilización y temperatura vía la API NVML (más robusto que `nvidia-smi`). Para usarlo sigue estos pasos:

1. Asegúrate de que `nvml.h` y `libnvidia-ml.so` estén presentes. En muchas instalaciones de CUDA el header está en `/usr/local/cuda/include/nvml.h` y la librería en `/usr/lib64/libnvidia-ml.so`.
	- Verifica con:

```bash
find /usr/local/cuda-*/include -name nvml.h
ls -l /usr/lib64/libnvidia-ml.so
```

2. Compila el proyecto (CMake detectará NVML y construirá `gpu_monitor_nvml` si los headers/libs están disponibles):

```bash
cd benchmark/gpu_benchmark
mkdir -p build && cd build
cmake .. -DCMAKE_CUDA_COMPILER=$(command -v nvcc)
make -j 2
```

3. Ejecuta el runner: `run_gpu_benchmark.sh` invocará `gpu_monitor_nvml` automáticamente cuando esté disponible y generará `results_gpu.csv` con métricas agregadas.

VS Code / IntelliSense
----------------------
Si ves errores tipo "cannot open source file 'nvml.h'" en VS Code: la extensión C/C++ necesita que el include path contenga la ruta al header de NVML.

Recomendaciones:

- He añadido configuraciones de IntelliSense en `.vscode/c_cpp_properties.json` en la raíz del repo y en `benchmark/gpu_benchmark/.vscode/` apuntando a `/usr/local/cuda-13.0/include`. Si abres `benchmark/gpu_benchmark` como carpeta, la configuración local será usada.
- Después de editar el includePath recarga VS Code: `Developer: Reload Window`.
- Si usas otro compilador o paths de include, ajusta `compilerPath` e `includePath` en el archivo `.vscode/c_cpp_properties.json`.

Debug rápido de NVML
-------------------
- Si `cmake` no detecta NVML pero sabes que `nvml.h` está instalado, indica explícitamente la ruta de include y library a CMake:

```bash
cmake .. -DNVML_INCLUDE_DIR=/usr/local/cuda-13.0/include -DNVML_LIBRARY=/usr/lib64/libnvidia-ml.so -DCMAKE_CUDA_COMPILER=$(command -v nvcc)
```

- Si no tienes los headers, en distribuciones basadas en Debian/Ubuntu puede haber paquetes como `libnvidia-ml-dev`. En sistemas con driver/CUDA instalados suele venir con el toolkit/driver.

Notas finales
---------------
- Si prefieres no depender de headers del sistema puedo añadir un monitor en Python que use `pynvml` (instalable con `pip install nvidia-ml-py3`) y hacer que `run_gpu_benchmark.sh` lo use automáticamente como fallback.
- Dime si quieres que añada forwarding de flags desde `run_gpu_benchmark.sh` a `gemm_benchmark_google` (útil para `--benchmark_repetitions` y otros).

Controlar iteraciones y repeticiones
- Versión simple (`gemm_benchmark`): edita la variable `ITERATIONS` dentro de `run_gpu_benchmark.sh` (valor por defecto reducido para pruebas rápidas). También puedes ejecutar el binario directamente:

```bash
./build/gemm_benchmark 1024 1024 1024 5   # M K N iterations
```

- Versión Google Benchmark (`gemm_benchmark_google`): Google Benchmark maneja iteraciones y repeticiones. Pasa flags al binario directamente para control fino:

```bash
./build/gemm_benchmark_google --benchmark_repetitions=5 --benchmark_iterations=100 --benchmark_min_time=0.1 --benchmark_format=json > /tmp/gb.json
```

El script `run_gpu_benchmark.sh` usa `gemm_benchmark_google` si está presente. Si necesitas pasar flags desde el script, dímelo y puedo añadir forwarding de argumentos.

Cómo variar el "stress"
- Incrementa los tamaños del problema en la variable `SIZES` dentro de `run_gpu_benchmark.sh`.
- Aumenta `ITERATIONS` (versión simple) o `--benchmark_repetitions`/`--benchmark_iterations` (Google Benchmark) para mayor duración y estabilidad.
- Reduce `SAMPLE_MS` (muestreo `nvidia-smi`) para mayor resolución (aumenta overhead).

Limitaciones y mejoras posibles
- Para contadores por-kernel (hardware counters) usa Nsight Compute / Nsight Systems o integra NVML/perf APIs — esto requiere trabajo adicional.
- NVML puede usarse para lecturas más robustas y sin depender del parsing de `nvidia-smi`.
- Ejecutar cada benchmark por separado y muestrear `nvidia-smi` durante la ejecución proporciona medidas por-size más precisas (más lento pero más exacto).

Contribuciones
- Si quieres que el script acepte flags y los reenvíe al binario Google Benchmark, lo añado rápido.

