# 📊 Benchmark Monitor C++ - Sistema de Microbenchmarking con Monitoreo

Sistema completo de microbenchmarking en C++ usando **Google Benchmark** con recolección exhaustiva de métricas de rendimiento, CPU y energía.

## 🎯 Características

- ✅ **Basado en Google Benchmark**: Usa la librería profesional de Google
- ✅ **5 Microbenchmarks implementados**:
  - Vector Add (suma vectorial)
  - Dot Product (producto punto)
  - MemCpy (copia optimizada)
  - Loop Copy (copia manual)
  - Matrix Multiply (multiplicación de matrices)
- ✅ **Métricas de sistema completas**:
  - CPU: frecuencia, governor, uso, threads
  - Energía: RAPL (Intel)
  - Rendimiento: perf stat (instructions, cycles, IPC, cache-misses, branch-misses)
  - Derivadas: IPC, EDP, power_avg
  - Temperatura de CPU
- ✅ **Salida CSV** con 18 columnas de métricas
- ✅ **Compilación automática** con CMake
- ✅ **Integración con perf stat** para métricas detalladas

## 📁 Estructura del Proyecto

```
benchmark_monitor_C/
├── benchmark_monitor.cpp          ⭐ Microbenchmarks principales
├── system_monitor.h               📊 Header de monitoreo de sistema
├── system_monitor.cpp             🔧 Implementación de métricas
├── CMakeLists.txt                 🏗️  Configuración de compilación
├── build.sh                       🔨 Script de compilación automática
├── run_benchmark_with_perf.sh     🚀 Ejecutor con perf stat
├── primer_benchmark.cpp           📚 Benchmark de ejemplo original
└── README.md                      📖 Este archivo
```

## 🚀 Quick Start

### 1. Compilar el proyecto

```bash
cd benchmark_monitor_C
./build.sh
```

Este script:
- ✅ Verifica que Google Benchmark esté compilado (si no, lo compila automáticamente)
- ✅ Configura el proyecto con CMake
- ✅ Compila el binario `benchmark_monitor`

### 2. Ejecutar benchmarks

**Opción A: Ejecución simple**
```bash
./benchmark_monitor
```

**Opción B: Con métricas de perf (recomendado)**
```bash
sudo ./run_benchmark_with_perf.sh
```

### 3. Ver resultados

Los resultados se guardan en `results_cpp.csv`:

```bash
cat results_cpp.csv
# O con formato de tabla:
column -t -s, results_cpp.csv | less -S
```

## 📊 Salida Generada

### Archivo CSV: `results_cpp.csv`

18 columnas con métricas completas:

```csv
timestamp,benchmark,N,cpu_freq_MHz,cpu_governor,cpu_usage_pct,threads,
instructions,cycles,ipc,cache_misses,branch_misses,
energy_uj,energy_J,time_s,edp,power_avg_W,temperature_C
```

### Ejemplo de salida en consola:

```
================================================================================
BENCHMARK MONITOR C++ - Sistema de Microbenchmarking
================================================================================

🔍 Configuración del sistema:
   CPU Cores: 16
   CPU Freq: 2400.0 MHz
   Governor: performance
   ✅ RAPL disponible

🚀 Ejecutando benchmarks...

BM_VectorAdd/16384: 0.125 ms, Energy: 0.000015 J, Temp: 52.3 °C
BM_VectorAdd/65536: 0.487 ms, Energy: 0.000058 J, Temp: 52.5 °C
BM_VectorAdd/262144: 1.923 ms, Energy: 0.000231 J, Temp: 52.8 °C
...

================================================================================
✅ Benchmarks completados
📊 Resultados guardados en: results_cpp.csv
================================================================================
```

## 🔧 Requisitos del Sistema

### Software
- **OS**: Linux (Ubuntu/Debian/Fedora)
- **Compilador**: g++ 7.0+ o clang++ 5.0+
- **CMake**: 3.10+
- **Google Benchmark**: Incluido en el repo (se compila automáticamente)
- **perf**: linux-tools (para métricas de rendimiento)

### Hardware
- **CPU**: Intel con RAPL (AMD funciona con métricas limitadas)
- **Arquitectura**: x86_64

### Instalación de dependencias

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install build-essential cmake git
sudo apt-get install linux-tools-common linux-tools-generic
```

**Fedora:**
```bash
sudo dnf install gcc-c++ cmake git
sudo dnf install perf
```

## 📖 Documentación Detallada

### Microbenchmarks Implementados

#### 1. **BM_VectorAdd** - Suma Vectorial
```cpp
c[i] = a[i] + b[i]  // Para cada elemento
```
- **Tipo**: Memory-bound
- **Tamaños**: 16K a 1M elementos
- **Uso**: Medir bandwidth de memoria

#### 2. **BM_DotProduct** - Producto Punto
```cpp
result = Σ(a[i] × b[i])
```
- **Tipo**: Compute-bound
- **Tamaños**: 16K a 1M elementos
- **Uso**: Medir capacidad de cómputo FP

#### 3. **BM_MemCpy** - Copia Optimizada
```cpp
memcpy(dst, src, N)
```
- **Tipo**: Memory bandwidth
- **Tamaños**: 16K a 16M bytes
- **Uso**: Medir ancho de banda máximo

#### 4. **BM_LoopCopy** - Copia Manual
```cpp
for (i = 0; i < N; i++) dst[i] = src[i]
```
- **Tipo**: Memory bandwidth
- **Uso**: Comparar con memcpy optimizado

#### 5. **BM_MatrixMultiply** - Multiplicación de Matrices
```cpp
C = A × B  // Naive implementation
```
- **Tamaños**: 32×32, 64×64, 128×128
- **Uso**: Operación intensiva en cómputo

### Métricas Recolectadas

#### CPU Info
- `cpu_freq_MHz`: Frecuencia actual de CPU
- `cpu_governor`: Governor activo (performance/powersave)
- `cpu_usage_pct`: Porcentaje de uso
- `threads`: Número de threads/cores

#### Perf Metrics (con perf stat)
- `instructions`: Instrucciones ejecutadas
- `cycles`: Ciclos de CPU
- `ipc`: Instructions Per Cycle (calculado)
- `cache_misses`: Fallos de caché
- `branch_misses`: Fallos de predicción de saltos

#### Energy Metrics (RAPL)
- `energy_uj`: Energía consumida en microjoules
- `energy_J`: Energía consumida en joules
- `power_avg_W`: Potencia promedio en watts

#### Métricas Derivadas
- `ipc`: IPC = instructions / cycles
- `edp`: EDP = energy × time²
- `power_avg_W`: Power = energy / time

## 🔍 Análisis de Resultados

### Ver métricas específicas

```bash
# Ver solo tiempos
cut -d',' -f2,3,15 results_cpp.csv

# Ver solo energía
cut -d',' -f2,3,13,14 results_cpp.csv

# Filtrar por benchmark específico
grep "VectorAdd" results_cpp.csv
```

## ⚙️ Configuración

### Modificar tamaños de datos

Edita `benchmark_monitor.cpp`:

```cpp
// Cambiar rangos de tamaños
BENCHMARK(BM_VectorAdd)->Range(1<<14, 1<<20);  // 16K a 1M
// A:
BENCHMARK(BM_VectorAdd)->Range(1<<10, 1<<24);  // 1K a 16M
```

### Modificar optimizaciones del compilador

Edita `CMakeLists.txt`:

```cmake
# Cambiar nivel de optimización
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native")
# A:
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2")  # Menos agresivo
```

### Añadir nuevos benchmarks

En `benchmark_monitor.cpp`:

```cpp
static void BM_MiNuevoBenchmark(benchmark::State& state) {
    const int64_t N = state.range(0);
    
    // Setup
    std::vector<int> data(N);
    
    for (auto _ : state) {
        // Tu código aquí
        benchmark::DoNotOptimize(data.data());
    }
}

BENCHMARK(BM_MiNuevoBenchmark)->Range(1<<10, 1<<20);
```


## 📚 Referencias

- **Google Benchmark**: https://github.com/google/benchmark
- **RAPL**: Intel Running Average Power Limit
- **perf**: Linux Performance Counter Subsystem
- **IPC**: Instructions Per Cycle
- **EDP**: Energy Delay Product

