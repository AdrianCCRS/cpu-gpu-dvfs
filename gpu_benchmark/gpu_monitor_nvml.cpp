// gpu_monitor_nvml.cpp
// Simple NVML-based monitor that launches a child process (the benchmark), samples NVML
// at a given interval, and writes aggregated statistics to an output file.

#include <nvml.h>
#include <unistd.h>
#include <sys/wait.h>
#include <chrono>
#include <thread>
#include <vector>
#include <string>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <cstdlib>
#include <cstring>
#include <ctime>

int main(int argc, char** argv) {
    if (argc < 4) {
        std::cerr << "Usage: " << argv[0] << " <sample_ms> <output_file> <command> [args...]\n";
        return 2;
    }

    int sample_ms = std::atoi(argv[1]);
    const char* out_file = argv[2];

    // Build command args for exec
    char** cmd = &argv[3];

    // Fork and exec the benchmark command
    pid_t pid = fork();
    if (pid == -1) {
        perror("fork");
        return 3;
    }

    if (pid == 0) {
        // child
        execvp(cmd[0], cmd);
        // if execvp returns, error
        perror("execvp");
        _exit(127);
    }

    // parent: monitor child
    nvmlReturn_t ret = nvmlInit();
    if (ret != NVML_SUCCESS) {
        std::cerr << "NVML init failed: " << nvmlErrorString(ret) << "\n";
        // still wait for child to finish
        int status = 0;
        waitpid(pid, &status, 0);
        return 4;
    }

    nvmlDevice_t device;
    ret = nvmlDeviceGetHandleByIndex(0, &device);
    if (ret != NVML_SUCCESS) {
        std::cerr << "NVML get device failed: " << nvmlErrorString(ret) << "\n";
        nvmlShutdown();
        int status = 0;
        waitpid(pid, &status, 0);
        return 5;
    }

    std::vector<double> powers; // watts
    std::vector<unsigned int> core_clocks;
    std::vector<unsigned int> mem_clocks;
    std::vector<unsigned int> utils; // percent
    std::vector<unsigned int> temps; // C

    auto t_start = std::chrono::steady_clock::now();

    // Loop until child exits
    int status = 0;
    while (true) {
        // non-blocking check if child is alive
        pid_t r = waitpid(pid, &status, WNOHANG);
        bool child_done = (r == pid);

        // sample
    unsigned int power_mw = 0;
        ret = nvmlDeviceGetPowerUsage(device, &power_mw);
        double power_w = (ret == NVML_SUCCESS) ? (power_mw / 1000.0) : 0.0;

    unsigned int core_mhz = 0;
    ret = nvmlDeviceGetClockInfo(device, NVML_CLOCK_GRAPHICS, &core_mhz);
    unsigned int core_mhz_val = (ret == NVML_SUCCESS) ? core_mhz : 0;

    unsigned int mem_mhz = 0;
    ret = nvmlDeviceGetClockInfo(device, NVML_CLOCK_MEM, &mem_mhz);
    unsigned int mem_mhz_val = (ret == NVML_SUCCESS) ? mem_mhz : 0;

        nvmlUtilization_t util;
        ret = nvmlDeviceGetUtilizationRates(device, &util);
        unsigned int gpu_util = (ret == NVML_SUCCESS) ? util.gpu : 0;

        unsigned int temp = 0;
        ret = nvmlDeviceGetTemperature(device, NVML_TEMPERATURE_GPU, &temp);
        unsigned int tval = (ret == NVML_SUCCESS) ? temp : 0;

    powers.push_back(power_w);
    core_clocks.push_back(core_mhz_val);
    mem_clocks.push_back(mem_mhz_val);
        utils.push_back(gpu_util);
        temps.push_back(tval);

        if (child_done) break;

        std::this_thread::sleep_for(std::chrono::milliseconds(sample_ms));
    }

    auto t_end = std::chrono::steady_clock::now();
    std::chrono::duration<double> dur = t_end - t_start;
    double duration_s = dur.count();

    // compute averages
    double sum_p = 0.0;
    long sum_core = 0, sum_mem = 0, sum_util = 0, sum_temp = 0;
    size_t n = powers.size();
    for (size_t i = 0; i < n; ++i) {
        sum_p += powers[i];
        sum_core += core_clocks[i];
        sum_mem += mem_clocks[i];
        sum_util += utils[i];
        sum_temp += temps[i];
    }

    double avg_p = (n>0) ? (sum_p / n) : 0.0;
    double avg_core = (n>0) ? (double)sum_core / n : 0.0;
    double avg_mem = (n>0) ? (double)sum_mem / n : 0.0;
    double avg_util = (n>0) ? (double)sum_util / n : 0.0;
    double avg_temp = (n>0) ? (double)sum_temp / n : 0.0;

    double energy_j = avg_p * duration_s;

    // Write to output file as key=value lines
    std::ofstream ofs(out_file, std::ios::out | std::ios::trunc);
    if (!ofs) {
        std::cerr << "Failed to open output file: " << out_file << "\n";
        nvmlShutdown();
        return 6;
    }
    // timestamp ISO
    auto now = std::chrono::system_clock::now();
    std::time_t now_t = std::chrono::system_clock::to_time_t(now);
    char buf[64];
    std::strftime(buf, sizeof(buf), "%FT%T%z", std::localtime(&now_t));

    ofs << "timestamp=" << buf << "\n";
    ofs << std::fixed << std::setprecision(3);
    ofs << "power_avg_w=" << avg_p << "\n";
    ofs << "gpu_core_clock_MHz=" << avg_core << "\n";
    ofs << "gpu_mem_clock_MHz=" << avg_mem << "\n";
    ofs << "gpu_utilization_pct=" << avg_util << "\n";
    ofs << "gpu_temp_c=" << avg_temp << "\n";
    ofs << "samples=" << n << "\n";
    ofs << "duration_s=" << duration_s << "\n";
    ofs << "energy_j=" << energy_j << "\n";
    ofs.close();

    nvmlShutdown();

    // Return child's exit status
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    if (WIFSIGNALED(status)) return 128 + WTERMSIG(status);
    return 0;
}
