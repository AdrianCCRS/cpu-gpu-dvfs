// system_monitor.h - Header para monitoreo de sistema (CPU, RAPL, temperatura)
#ifndef SYSTEM_MONITOR_H
#define SYSTEM_MONITOR_H

#include <string>
#include <vector>
#include <map>
#include <cstdint>

namespace system_monitor {

// ============================================================
// Estructuras de datos para métricas
// ============================================================

struct CPUInfo {
    double freq_mhz;
    std::string governor;
    double usage_pct;
    int num_threads;
};

struct PerfMetrics {
    uint64_t instructions;
    uint64_t cycles;
    uint64_t cache_misses;
    uint64_t branch_misses;
    double ipc;  // Instructions Per Cycle
};

struct EnergyMetrics {
    uint64_t energy_uj;      // microjoules
    double energy_j;         // joules
    double power_avg_w;      // watts
};

struct BenchmarkResult {
    std::string timestamp;
    std::string benchmark_name;
    int64_t data_size;
    
    CPUInfo cpu_info;
    PerfMetrics perf;
    EnergyMetrics energy;
    
    double time_s;
    double temperature_c;
    double edp;  // Energy Delay Product
};

// ============================================================
// Clase principal para monitoreo
// ============================================================

class SystemMonitor {
public:
    SystemMonitor();
    ~SystemMonitor();
    
    // Obtener información de CPU
    CPUInfo getCPUInfo();
    
    // Leer energía de RAPL (Intel)
    uint64_t readRAPLEnergy();
    
    // Obtener temperatura de CPU
    double getTemperature();
    
    // Verificar disponibilidad de características
    bool isRAPLAvailable();
    bool isPerfAvailable();
    
    // Calcular métricas derivadas
    static double calculateIPC(uint64_t instructions, uint64_t cycles);
    static double calculateEDP(double energy_j, double time_s);
    static double calculatePowerAvg(double energy_j, double time_s);
    
    // Parsear métricas de perf desde archivo
    static PerfMetrics parsePerfMetrics(const std::string& perf_output);
    
private:
    std::string rapl_path_;
    bool rapl_available_;
    bool perf_available_;
    
    // Helper para leer archivos del sistema
    std::string readSysFile(const std::string& path);
    uint64_t readSysFileUInt64(const std::string& path);
};

// ============================================================
// Utilidades para CSV
// ============================================================

class CSVWriter {
public:
    CSVWriter(const std::string& filename);
    ~CSVWriter();
    
    void writeHeader();
    void writeResult(const BenchmarkResult& result);
    void close();
    
private:
    std::string filename_;
    bool header_written_;
    FILE* file_;
};

} // namespace system_monitor

#endif // SYSTEM_MONITOR_H
