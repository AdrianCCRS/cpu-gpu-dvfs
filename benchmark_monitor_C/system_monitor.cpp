// system_monitor.cpp - Implementación del monitoreo de sistema
#include "system_monitor.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <cmath>
#include <ctime>
#include <iomanip>
#include <sys/stat.h>
#include <unistd.h>
#include <dirent.h>
#include <cstring>

namespace system_monitor {

// ============================================================
// Constructor y Destructor
// ============================================================

SystemMonitor::SystemMonitor() 
    : rapl_path_("/sys/class/powercap/intel-rapl"),
      rapl_available_(false),
      perf_available_(false) {
    
    // Verificar disponibilidad de RAPL
    struct stat st;
    rapl_available_ = (stat(rapl_path_.c_str(), &st) == 0);
    
    // Verificar disponibilidad de perf
    perf_available_ = (system("which perf > /dev/null 2>&1") == 0);
}

SystemMonitor::~SystemMonitor() {}

// ============================================================
// Métodos de lectura del sistema
// ============================================================

std::string SystemMonitor::readSysFile(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        return "";
    }
    
    std::string content;
    std::getline(file, content);
    file.close();
    
    return content;
}

uint64_t SystemMonitor::readSysFileUInt64(const std::string& path) {
    std::string content = readSysFile(path);
    if (content.empty()) {
        return 0;
    }
    
    try {
        return std::stoull(content);
    } catch (...) {
        return 0;
    }
}

CPUInfo SystemMonitor::getCPUInfo() {
    CPUInfo info;
    
    // Frecuencia de CPU (de /proc/cpuinfo o /sys)
    std::string freq_str = readSysFile("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq");
    if (!freq_str.empty()) {
        info.freq_mhz = std::stod(freq_str) / 1000.0;  // kHz a MHz
    } else {
        info.freq_mhz = 0.0;
    }
    
    // Governor
    info.governor = readSysFile("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor");
    
    // Número de threads (cores)
    info.num_threads = sysconf(_SC_NPROCESSORS_ONLN);
    
    // Uso de CPU (simplificado - en producción usarías muestreo)
    info.usage_pct = 0.0;  // Requeriría muestreo de /proc/stat
    
    return info;
}

uint64_t SystemMonitor::readRAPLEnergy() {
    if (!rapl_available_) {
        return 0;
    }
    
    // Buscar el dominio package-0 (o el primero disponible)
    DIR* dir = opendir(rapl_path_.c_str());
    if (!dir) {
        return 0;
    }
    
    uint64_t total_energy = 0;
    struct dirent* entry;
    
    while ((entry = readdir(dir)) != nullptr) {
        std::string dirname = entry->d_name;
        
        // Buscar intel-rapl:0 (package-0)
        if (dirname.find("intel-rapl:0") != std::string::npos) {
            std::string energy_path = rapl_path_ + "/" + dirname + "/energy_uj";
            total_energy = readSysFileUInt64(energy_path);
            break;
        }
    }
    
    closedir(dir);
    return total_energy;
}

double SystemMonitor::getTemperature() {
    // Intentar leer de diferentes fuentes de temperatura
    std::vector<std::string> temp_paths = {
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/thermal/thermal_zone1/temp",
        "/sys/class/hwmon/hwmon0/temp1_input",
        "/sys/class/hwmon/hwmon1/temp1_input"
    };
    
    for (const auto& path : temp_paths) {
        std::string temp_str = readSysFile(path);
        if (!temp_str.empty()) {
            try {
                // Temperatura suele estar en mili-grados Celsius
                return std::stod(temp_str) / 1000.0;
            } catch (...) {
                continue;
            }
        }
    }
    
    return 0.0;  // No disponible
}

bool SystemMonitor::isRAPLAvailable() {
    return rapl_available_;
}

bool SystemMonitor::isPerfAvailable() {
    return perf_available_;
}

// ============================================================
// Cálculo de métricas derivadas
// ============================================================

double SystemMonitor::calculateIPC(uint64_t instructions, uint64_t cycles) {
    if (cycles == 0) return 0.0;
    return static_cast<double>(instructions) / static_cast<double>(cycles);
}

double SystemMonitor::calculateEDP(double energy_j, double time_s) {
    return energy_j * time_s * time_s;
}

double SystemMonitor::calculatePowerAvg(double energy_j, double time_s) {
    if (time_s == 0.0) return 0.0;
    return energy_j / time_s;
}

// ============================================================
// Parser de métricas de perf
// ============================================================

PerfMetrics SystemMonitor::parsePerfMetrics(const std::string& perf_output) {
    PerfMetrics metrics = {0, 0, 0, 0, 0.0};
    
    std::istringstream stream(perf_output);
    std::string line;
    
    // Formato CSV de perf: valor,unidad,nombre_evento,...
    while (std::getline(stream, line)) {
        if (line.empty()) continue;
        
        std::istringstream line_stream(line);
        std::string value_str, unit, event;
        
        // Parsear CSV
        std::getline(line_stream, value_str, ',');
        std::getline(line_stream, unit, ',');
        std::getline(line_stream, event, ',');
        
        if (value_str.empty() || value_str == "<not counted>") {
            continue;
        }
        
        try {
            uint64_t value = std::stoull(value_str);
            
            if (event.find("instructions") != std::string::npos) {
                metrics.instructions = value;
            } else if (event.find("cycles") != std::string::npos && 
                       event.find("cache") == std::string::npos) {
                metrics.cycles = value;
            } else if (event.find("cache-misses") != std::string::npos) {
                metrics.cache_misses = value;
            } else if (event.find("branch-misses") != std::string::npos) {
                metrics.branch_misses = value;
            }
        } catch (...) {
            continue;
        }
    }
    
    // Calcular IPC
    metrics.ipc = calculateIPC(metrics.instructions, metrics.cycles);
    
    return metrics;
}

// ============================================================
// CSVWriter - Implementación
// ============================================================

CSVWriter::CSVWriter(const std::string& filename) 
    : filename_(filename), header_written_(false), file_(nullptr) {
    
    // Verificar si el archivo ya existe
    struct stat st;
    header_written_ = (stat(filename_.c_str(), &st) == 0);
    
    // Abrir en modo append
    file_ = fopen(filename_.c_str(), "a");
    if (!file_) {
        std::cerr << "Error: No se pudo abrir " << filename_ << std::endl;
    }
}

CSVWriter::~CSVWriter() {
    close();
}

void CSVWriter::writeHeader() {
    if (!file_ || header_written_) return;
    
    fprintf(file_, "timestamp,benchmark,N,cpu_freq_MHz,cpu_governor,cpu_usage_pct,threads,");
    fprintf(file_, "instructions,cycles,ipc,cache_misses,branch_misses,");
    fprintf(file_, "energy_uj,energy_J,time_s,edp,power_avg_W,temperature_C\n");
    
    fflush(file_);
    header_written_ = true;
}

void CSVWriter::writeResult(const BenchmarkResult& result) {
    if (!file_) return;
    
    // Escribir encabezado si no existe
    if (!header_written_) {
        writeHeader();
    }
    
    // Construir línea completa en un buffer para evitar saltos de línea
    char line_buffer[1024];
    snprintf(line_buffer, sizeof(line_buffer),
             "%s,%s,%ld,%.2f,%s,%.1f,%d,%lu,%lu,%.3f,%lu,%lu,%lu,%.6f,%.6f,%.2e,%.3f,%.1f\n",
             result.timestamp.c_str(),
             result.benchmark_name.c_str(),
             result.data_size,
             result.cpu_info.freq_mhz,
             result.cpu_info.governor.c_str(),
             result.cpu_info.usage_pct,
             result.cpu_info.num_threads,
             result.perf.instructions,
             result.perf.cycles,
             result.perf.ipc,
             result.perf.cache_misses,
             result.perf.branch_misses,
             result.energy.energy_uj,
             result.energy.energy_j,
             result.time_s,
             result.edp,
             result.energy.power_avg_w,
             result.temperature_c);
    
    // Escribir línea completa de una vez
    fputs(line_buffer, file_);
    fflush(file_);
}

void CSVWriter::close() {
    if (file_) {
        fclose(file_);
        file_ = nullptr;
    }
}

} // namespace system_monitor
