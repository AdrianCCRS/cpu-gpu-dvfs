// benchmark_monitor.cpp - Microbenchmarks con monitoreo de sistema completo
#include <benchmark/benchmark.h>
#include "system_monitor.h"
#include <vector>
#include <cstring>
#include <ctime>
#include <iomanip>
#include <sstream>
#include <iostream>
#include <unistd.h>  // Para geteuid()

using namespace system_monitor;

// ============================================================
// Variables globales para monitoreo
// ============================================================
static SystemMonitor* g_monitor = nullptr;
static CSVWriter* g_csv_writer = nullptr;
static uint64_t g_energy_start = 0;
static double g_temp_start = 0.0;

// ============================================================
// Utilidades
// ============================================================

std::string getCurrentTimestamp() {
    auto t = std::time(nullptr);
    auto tm = *std::localtime(&t);
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%dT%H:%M:%S");
    return oss.str();
}

// ============================================================
// BENCHMARK 1: Vector Add (Suma de Vectores)
// ============================================================
static void BM_VectorAdd(benchmark::State& state) {
    const int64_t N = state.range(0);
    
    std::vector<double> a(N, 1.0);
    std::vector<double> b(N, 2.0);
    std::vector<double> c(N, 0.0);
    
    // Medición inicial
    g_energy_start = g_monitor->readRAPLEnergy();
    g_temp_start = g_monitor->getTemperature();
    
    for (auto _ : state) {
        for (int64_t i = 0; i < N; i++) {
            c[i] = a[i] + b[i];
        }
        benchmark::DoNotOptimize(c.data());
        benchmark::ClobberMemory();
    }
    
    // Calcular bytes procesados
    state.SetBytesProcessed(state.iterations() * N * sizeof(double) * 3);
    state.SetItemsProcessed(state.iterations() * N);
}

BENCHMARK(BM_VectorAdd)->Range(1<<14, 1<<20)->Unit(benchmark::kMillisecond);

// ============================================================
// BENCHMARK 2: Dot Product (Producto Punto)
// ============================================================
static void BM_DotProduct(benchmark::State& state) {
    const int64_t N = state.range(0);
    
    std::vector<double> a(N, 1.5);
    std::vector<double> b(N, 2.5);
    
    g_energy_start = g_monitor->readRAPLEnergy();
    g_temp_start = g_monitor->getTemperature();
    
    for (auto _ : state) {
        double result = 0.0;
        for (int64_t i = 0; i < N; i++) {
            result += a[i] * b[i];
        }
        benchmark::DoNotOptimize(result);
    }
    
    // 2 operaciones por elemento (mul + add)
    state.SetItemsProcessed(state.iterations() * N * 2);
}

BENCHMARK(BM_DotProduct)->Range(1<<14, 1<<20)->Unit(benchmark::kMillisecond);

// ============================================================
// BENCHMARK 3: MemCpy (Copia de Memoria)
// ============================================================
static void BM_MemCpy(benchmark::State& state) {
    const int64_t N = state.range(0);
    
    std::vector<char> src(N, 'A');
    std::vector<char> dst(N, 'B');
    
    g_energy_start = g_monitor->readRAPLEnergy();
    g_temp_start = g_monitor->getTemperature();
    
    for (auto _ : state) {
        memcpy(dst.data(), src.data(), N);
        benchmark::ClobberMemory();
    }
    
    state.SetBytesProcessed(state.iterations() * N);
}

BENCHMARK(BM_MemCpy)->Range(1<<14, 1<<24)->Unit(benchmark::kMillisecond);

// ============================================================
// BENCHMARK 4: Loop Copy (comparación con memcpy)
// ============================================================
static void BM_LoopCopy(benchmark::State& state) {
    const int64_t N = state.range(0);
    
    std::vector<char> src(N, 'A');
    std::vector<char> dst(N, 'B');
    
    g_energy_start = g_monitor->readRAPLEnergy();
    g_temp_start = g_monitor->getTemperature();
    
    for (auto _ : state) {
        for (int64_t i = 0; i < N; i++) {
            dst[i] = src[i];
        }
        benchmark::ClobberMemory();
    }
    
    state.SetBytesProcessed(state.iterations() * N);
}

BENCHMARK(BM_LoopCopy)->Range(1<<14, 1<<24)->Unit(benchmark::kMillisecond);

// ============================================================
// BENCHMARK 5: Matrix Multiply (Multiplicación de Matrices)
// ============================================================
static void BM_MatrixMultiply(benchmark::State& state) {
    const int M = state.range(0);
    const int K = state.range(1);
    const int N = state.range(2);
    
    std::vector<float> A(M * K, 1.0f);
    std::vector<float> B(K * N, 2.0f);
    std::vector<float> C(M * N, 0.0f);
    
    g_energy_start = g_monitor->readRAPLEnergy();
    g_temp_start = g_monitor->getTemperature();
    
    for (auto _ : state) {
        for (int i = 0; i < M; i++) {
            for (int j = 0; j < N; j++) {
                float sum = 0.0f;
                for (int k = 0; k < K; k++) {
                    sum += A[i * K + k] * B[k * N + j];
                }
                C[i * N + j] = sum;
            }
        }
        benchmark::DoNotOptimize(C.data());
        benchmark::ClobberMemory();
    }
    
    // FLOPS = 2 * M * N * K
    state.SetItemsProcessed(state.iterations() * 2 * M * N * K);
}

BENCHMARK(BM_MatrixMultiply)->Args({32, 32, 32})
                             ->Args({64, 64, 64})
                             ->Args({128, 128, 128})
                             ->Unit(benchmark::kMillisecond);

// ============================================================
// Custom Reporter para CSV con métricas del sistema
// ============================================================
class SystemMetricsReporter : public benchmark::BenchmarkReporter {
public:
    SystemMetricsReporter() : monitor_(new SystemMonitor()) {
        csv_writer_ = new CSVWriter("results_cpp.csv");
    }
    
    ~SystemMetricsReporter() {
        if (csv_writer_) {
            csv_writer_->close();
            delete csv_writer_;
        }
        delete monitor_;
    }
    
    bool ReportContext(const Context& context) override {
        std::cout << "\n" << std::string(80, '=') << std::endl;
        std::cout << "BENCHMARK MONITOR C++ - Sistema de Microbenchmarking" << std::endl;
        std::cout << std::string(80, '=') << std::endl;
        
        std::cout << "\n🔍 Configuración del sistema:" << std::endl;
        
        auto cpu_info = monitor_->getCPUInfo();
        std::cout << "   CPU Cores: " << cpu_info.num_threads << std::endl;
        std::cout << "   CPU Freq: " << cpu_info.freq_mhz << " MHz" << std::endl;
        std::cout << "   Governor: " << cpu_info.governor << std::endl;
        
        if (monitor_->isRAPLAvailable()) {
            std::cout << "   ✅ RAPL disponible" << std::endl;
        } else {
            std::cout << "   ⚠️  RAPL no disponible" << std::endl;
        }
        
        std::cout << "\n🚀 Ejecutando benchmarks...\n" << std::endl;
        
        return true;
    }
    
    void ReportRuns(const std::vector<Run>& reports) override {
        for (const auto& run : reports) {
            // Verificar si el benchmark se ejecutó correctamente
            if (run.skipped) continue;
            
            // Crear resultado
            BenchmarkResult result;
            result.timestamp = getCurrentTimestamp();
            result.benchmark_name = run.benchmark_name();
            
            // Extraer tamaño de datos del nombre del benchmark
            // Formato: BM_VectorAdd/16384
            size_t slash_pos = run.benchmark_name().find('/');
            if (slash_pos != std::string::npos) {
                std::string size_str = run.benchmark_name().substr(slash_pos + 1);
                result.data_size = std::stoll(size_str);
            } else {
                result.data_size = 0;
            }
            
            // CPU info
            result.cpu_info = monitor_->getCPUInfo();
            
            // Tiempo
            result.time_s = run.GetAdjustedRealTime() / 1e9;  // ns a s
            
            // Energía
            uint64_t energy_end = monitor_->readRAPLEnergy();
            result.energy.energy_uj = energy_end - g_energy_start;
            result.energy.energy_j = result.energy.energy_uj / 1e6;
            result.energy.power_avg_w = SystemMonitor::calculatePowerAvg(
                result.energy.energy_j, result.time_s);
            
            // Temperatura
            result.temperature_c = monitor_->getTemperature();
            
            // EDP
            result.edp = SystemMonitor::calculateEDP(
                result.energy.energy_j, result.time_s);
            
            // Perf metrics (se llenarán desde el wrapper de perf)
            // Por ahora, valores por defecto
            result.perf.instructions = 0;
            result.perf.cycles = 0;
            result.perf.ipc = 0.0;
            result.perf.cache_misses = 0;
            result.perf.branch_misses = 0;
            
            // Escribir a CSV
            csv_writer_->writeResult(result);
            
            // Mostrar en consola
            std::cout << "  " << run.benchmark_name() 
                      << ": " << run.GetAdjustedRealTime() / 1e6 << " ms"
                      << ", Energy: " << result.energy.energy_j << " J"
                      << ", Temp: " << result.temperature_c << " °C"
                      << std::endl;
        }
    }
    
    void Finalize() override {
        std::cout << "\n" << std::string(80, '=') << std::endl;
        std::cout << "✅ Benchmarks completados" << std::endl;
        std::cout << "📊 Resultados guardados en: results_cpp.csv" << std::endl;
        std::cout << std::string(80, '=') << std::endl << std::endl;
    }
    
private:
    SystemMonitor* monitor_;
    CSVWriter* csv_writer_;
};

// ============================================================
// MAIN
// ============================================================
int main(int argc, char** argv) {
    // Inicializar monitor global
    g_monitor = new SystemMonitor();
    
    // Verificar permisos
    if (geteuid() != 0) {
        std::cout << "⚠️  Advertencia: No estás ejecutando como root (sudo)" << std::endl;
        std::cout << "   Las métricas de RAPL pueden no estar disponibles" << std::endl;
        std::cout << std::endl;
    }
    
    // Configurar reporter personalizado
    SystemMetricsReporter reporter;
    benchmark::Initialize(&argc, argv);
    benchmark::RunSpecifiedBenchmarks(&reporter);
    
    // Cleanup
    delete g_monitor;
    
    return 0;
}
